from time import time, sleep
from datetime import datetime, timedelta
import json
import threading
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

    def __init__(self, id, name, updated, state=None):
        self.id = id
        self.name = name
        self.started = None
        self.updated = updated
        if state:
            self.state = state
        else:
            self.state = SupervisorProcess.UNKNOWN
        self.subscribers = []

    def subscribe(self, client):
        if client not in self.subscribers:
            self.subscribers.append(client)

    def unsubscribe(self, client):
        if client in self.subscribers:
            self.subscribers.remove(client)

    def update(self, started, state, updated=None):
        self.started = started
        if updated:
            self.updated = updated
        if state in type(self).States:
            self.state = state
            for client in self.subscribers:
                data = self.__json__()
                data.update(id=self.id)
                client.ws.write_message(json.dumps(data))

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
        self.clients = {}
        for agent in dal.session.query(Agent).all():
            info = AgentInfo(agent)
            result = pal.query('SELECT process_name AS process, ' \
                'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
                'WHERE agent_id = "{0}" GROUP BY process_name;'.format(agent.id), 'P6W')
            for row in json.loads(result):
                info.add(SupervisorProcess(info.id, row['process'],
                    datetime.utcfromtimestamp(float(row['time'])/1000.0)))
            self.agents[info.id] = info

    def update(self, id, process, started, state, updated=None):
        self.agents[id].processes[process].update(started, state, updated)

    def subscribe(self, client, id, process):
        self.agents[id].processes[process].subscribe(client)

        if client not in self.clients:
            self.clients[client] = [(id, process)]
            def push_stats(*args):
                while client in self.clients:
                    print('push_stats')
                    sleep(1.0)
                print('DONE WITH THREAD!')

            thread = threading.Thread(target=push_stats)
            thread.start()
        elif (id, process) not in self.clients[client]:
            self.clients[client].append((id, process))

    def unsubscribe(self, client, id, process):
        self.agents[id].processes[process].unsubscribe(client)

        if client in self.clients and (id, process) in self.clients[client]:
            self.clients[client].remove((id, process))
            if len(self.clients[client]) == 0:
                self.clients.pop(client, None)

    def unsubscribe_all(self, client):
        if client in self.clients:
            for (id, process) in self.clients[client]:
                self.agents[id].processes[process].unsubscribe(client)
            self.clients.pop(client)

    def __repr__(self):
        return "<SupervisorClientCoordinator(agents={self.agents})>".format(self=self)

    def __json__(self):
        return [val.__json__() for val in self.agents.values()]


scc = SupervisorClientCoordinator()
