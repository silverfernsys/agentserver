import json
import threading
from time import time, sleep
from datetime import datetime, timedelta
from tornado.escape import json_encode
from db.models import Agent
from db.timeseries import dral
from utils.iso_8601 import (iso_8601_period_to_timedelta,
    iso_8601_interval_to_datetimes)


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

    def __init__(self, id, name, started, updated, state=None):
        self.id = id
        self.name = name
        self.started = started
        self.updated = updated
        if state:
            self.state = state
        else:
            self.state = self.UNKNOWN
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
        if state in self.States:
            self.state = state
            data = {'state': self.__json__()}
            for client in self.subscribers:
                client.ws.write_message(json_encode(data))

    def __repr__(self):
        return "<SupervisorProcess(name={0}, " \
            "updated={1}, started={2}, state={3})>".format(self.name,
                self.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                self.started, self.state)

    def __json__(self):
        if self.started:
            started = self.started.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            started = self.UNKNOWN

        if self.updated:
            updated = self.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            updated = self.UNKNOWN

        return {'id': self.id, 'name': self.name, 'updated': updated,
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
        self.updates = {}

        for agent in Agent.all():
            info = AgentInfo(agent)
            result = dral.processes(agent.id, 'P6W')
            for row in result:
                info.add(SupervisorProcess(info.id, row['process'], None,
                    datetime.utcfromtimestamp(float(row['time'])/1000.0)))
            self.agents[info.id] = info

    def destroy(self):
        pass

    def update(self, id, name, start, statename, **kwargs):
        stats = kwargs.get('stats', None)
        if stats and len(stats) > 0:
            updated = datetime.utcfromtimestamp(stats[-1][0])
        else:
            updated = datetime.utcnow()

        started = datetime.utcfromtimestamp(start)

        if name not in self.agents[id].processes:
            self.agents[id].add(SupervisorProcess(id, name, started, statename, updated))
        else:
            self.agents[id].processes[name].update(started, statename, updated)

    def subscribe(self, client, id, process, granularity='P3D', intervals='P6W', **kwargs):
        dral.__validate_granularity__(granularity, dral.timeseries_granularities)
        dral.__validate_intervals__(intervals)

        (start, end) = iso_8601_interval_to_datetimes(intervals)

        self.agents[id].processes[process].subscribe(client)

        if client not in self.clients:
            self.clients[client] = [(id, process)]
            self.updates[(client, id, process)] = (granularity, (start, end))
            def push_stats(*args):
                while client in self.clients:
                    for (id, process) in self.clients[client]:
                        (granularity, (start, end)) = self.updates[(client, id, process)]
                        result = dral.timeseries(id, process, granularity=granularity,
                            intervals=intervals).result
                        body = {'snapshot': {'id': id, 'process': process,
                            'stats': map(lambda x: {'timestamp': x['timestamp'],
                            'cpu': x['result']['cpu'], 'mem': x['result']['mem']}, result)}}
                        client.ws.write_message(json_encode(body))
                        # print('result: %s' % result)
                        # Note: when end != None and start > end, remove key from self.updates
                        sleep(1.0)   
                print('DONE WITH THREAD!')
            thread = threading.Thread(target=push_stats)
            thread.start()
        elif (id, process) not in self.clients[client]:
            self.clients[client].append((id, process))
        # Create a new key if it doesn't exist, or update value if it does.
        self.updates[(client, id, process)] = (granularity, (start, end))

    def unsubscribe(self, client, id, process, **kwargs):
        self.agents[id].processes[process].unsubscribe(client)

        if client in self.clients and (id, process) in self.clients[client]:
            self.clients[client].remove((id, process))
            if len(self.clients[client]) == 0:
                self.clients.pop(client, None)
        if (client, id, process) in self.updates:
            self.updates.pop((client, id, process), None)

    def unsubscribe_all(self, client):
        if client in self.clients:
            for (id, process) in self.clients[client]:
                self.updates.pop((client, id, process), None)
                self.agents[id].processes[process].unsubscribe(client)
            self.clients.pop(client)

    def __repr__(self):
        return "<SupervisorClientCoordinator(agents={self.agents})>".format(self=self)

    def __json__(self):
        return [val.__json__() for val in self.agents.values()]


scc = SupervisorClientCoordinator()
