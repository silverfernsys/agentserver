from time import time
from datetime import datetime, timedelta
import json
from sqlalchemy.orm.exc import NoResultFound
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension
from db import dal, pal, Agent


class SupervisorProcess(object):
    STOPPED = 'STOPPED'
    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    BACKOFF = 'BACKOFF'
    STOPPING = 'STOPPING'
    EXITED = 'EXITED'
    FATAL = 'FATAL'
    UNKNOWN = 'UNKNOWN'

    States = set([STOPPED, STARTING, RUNNING, BACKOFF,
        STOPPING, EXITED, FATAL, UNKNOWN])

    def __init__(self, name, updated, state=None):
        self.name = name
        self.started = None
        self.updated = updated
        if state:
            self.state = state
        else:
            self.state = SupervisorProcess.UNKNOWN

    def update(started, updated, state):
        self.started = started
        self.updated = updated
        if state in type(self).States:
            self.state = state

    def __repr__(self):
        return "<SupervisorProcess(name={0}, " \
            "updated={1}, started={2}, state={3})>".format(self.name,
                self.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                self.started, self.state)

    def __json__(self):
        if self.started:
            started = self.started.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            started = type(self).UNKNOWN

        return {'name': self.name, 'updated': self.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'started': started, 'state': self.state}    


class AgentInfo(object):
    DISCONNECTED = 'DISCONNECTED'
    CONNECTED = 'CONNECTED'

    States = set([DISCONNECTED, CONNECTED])

    def __init__(self, agent, state=None):
        self.name = agent.name
        self.id = agent.id
        if state:
            self.state = state
        else:
            self.state = AgentInfo.DISCONNECTED
        self.processes = {}

    def add(self, process):
        self.processes[process.name] = process

    def __repr__(self):
        return "<AgentInfo(id={self.id}, " \
            "name={self.name}, state={self.state}, " \
            "processes={self.processes})>".format(self=self)

    def __json__(self):
        return {'name': self.name, 'id': self.id, 'state': self.state,
            'processes': [val.__json__() for val in self.processes.values()]}


class SupervisorClientCoordinator(object):
    def initialize(self):
        self.agents = {} 
        for agent in dal.session.query(Agent).all():
            info = AgentInfo(agent)
            result = pal.query('SELECT process_name AS process, ' \
                'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
                'WHERE agent_id = "{0}" GROUP BY process_name;'.format(agent.id), 'P6W')
            data = json.loads(result)
            for row in data:
                info.add(SupervisorProcess(row['process'],
                    datetime.utcfromtimestamp(float(row['time'])/1000.0)))
            self.agents[info.id] = info

    def __json__(self):
        return [val.__json__() for val in self.agents.values()]


scc = SupervisorClientCoordinator()
