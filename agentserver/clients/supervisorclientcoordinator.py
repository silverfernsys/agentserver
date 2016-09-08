import threading
from time import sleep
from datetime import datetime
from iso8601utils import parsers
from tornado.escape import json_encode
from agentserver.db.models import Agent
from agentserver.db.timeseries import druid


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
        updated = self.updated.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        started = self.started.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return '<SupervisorProcess(name={0}, updated={1}, '
        'started={2}, state={3})>'.format(self.name, updated,
                                          started, self.state)

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
        processes = [val.__json__() for val in self.processes.values()]
        return {'name': self.name, 'id': self.id, 'state': self.state,
                'processes': processes}


class SupervisorClientCoordinator(object):

    def initialize(self):
        self.agents = {}
        self.clients = {}
        self.updates = {}

        for agent in Agent.all():
            info = AgentInfo(agent)
            result = druid.processes(agent.id, 'P6W')
            for row in result:
                timestamp = float(row['time']) / 1000.0
                updated = datetime.utcfromtimestamp(timestamp)
                info.add(SupervisorProcess(info.id, row['process'],
                                           None, updated))
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
            self.agents[id].add(SupervisorProcess(
                id, name, started, statename, updated))
        else:
            self.agents[id].processes[name].update(started, statename, updated)

    def subscribe(self, client, id, process, granularity='P3D',
                  intervals='P6W', **kwargs):
        druid.__validate_granularity__(
            granularity, druid.timeseries_granularities)
        druid.__validate_intervals__(intervals)

        (start, end) = parsers.interval(intervals)

        self.agents[id].processes[process].subscribe(client)

        if client not in self.clients:
            self.clients[client] = [(id, process)]
            self.updates[(client, id, process)] = (granularity, (start, end))

            def push_stats(*args):
                while client in self.clients:
                    for (id, process) in self.clients[client]:
                        (granularity, (start, end)) = self.updates[
                            (client, id, process)]
                        result = druid.timeseries(id, process, granularity,
                                                  intervals).result
                        stats = map(lambda x: {'timestamp': x['timestamp'],
                                               'cpu': x['result']['cpu'],
                                               'mem': x['result']['mem']},
                                    result)
                        body = {'snapshot': {'id': id, 'process': process,
                                             'stats': stats}}
                        client.ws.write_message(json_encode(body))
                        # print('result: %s' % result)
                        # Note: when end != None and start > end, remove key
                        # from self.updates
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

    # def push_stats(self, *args):

    def __repr__(self):
        return '<SupervisorClientCoordinator(agents='
        '{self.agents})>'.format(self=self)

    def __json__(self):
        return [val.__json__() for val in self.agents.values()]


scc = SupervisorClientCoordinator()
