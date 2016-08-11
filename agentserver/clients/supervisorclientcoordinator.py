from time import time
from datetime import datetime, timedelta
import json
from sqlalchemy.orm.exc import NoResultFound
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension
from db import dal, pal, Agent


class SupervisorProcess(json.JSONEncoder):
    def __init__(self, name, updated, state):
        self.name = name
        self.updated = updated
        self.state = state

    def __repr__(self):
        return "<SupervisorProcess(name={0}, " \
            "updated={1}, state={2})>".format(self.name,
                self.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), self.state)

    def __json__(self):
        return {'name': self.name, 'update': self.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'state': self.state}    


class SupervisorClientCoordinator(object):
    AGENTS = {}
    DISCONNECTED = 'DISCONNECTED'

    def initialize(self):
        agents = dal.session.query(Agent).all()
        for agent in agents:
            result = pal.query('SELECT process_name AS process, ' \
                'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
                'WHERE agent_id = "{0}" GROUP BY process_name;'.format(agent.id), 'P6W')
            data = json.loads(result)
            processes = {}
            for row in data:
                processes[row['process']] = SupervisorProcess(row['process'],
                    datetime.utcfromtimestamp(float(row['time'])/1000.0), type(self).DISCONNECTED)
            type(self).AGENTS[agent.name] = processes

    def __json__(self):
        return [key for key in type(self).AGENTS.keys()]


scc = SupervisorClientCoordinator()

    # def initialize(self):
    #     agents = dal.session.query(Agent).all()
    #     intervals = '{0}/p6w'.format((datetime.utcnow() - timedelta(weeks=6)).strftime("%Y-%m-%d"))
    #     # print(agents)
    #     for agent in agents:
    #         group = dral.connection.groupby(
    #             datasource='supervisor',
    #             granularity='all',
    #             intervals=intervals,
    #             dimensions=["process_name"],
    #             filter=(Dimension("agent_id") == agent.id),
    #             aggregations={"count": doublesum("count")})
    #         # print(type(group.result_json))
    #         # print(group.result_json)
    #         data = json.loads(group.result_json)
    #         processes = {}
    #         for row in data:
    #             if row['event']['count'] > 0:
    #                 processes[row['event']['process_name']] = 'disconnected'
    #         type(self).AGENTS[agent.name] = processes