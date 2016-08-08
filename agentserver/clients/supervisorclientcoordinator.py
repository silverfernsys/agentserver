from time import time
from datetime import datetime, timedelta
import json
from sqlalchemy.orm.exc import NoResultFound
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension
from db import dal, dral, Agent


class SupervisorClientCoordinator(object):
    AGENTS = {}

    def initialize(self):
        agents = dal.session.query(Agent).all()
        intervals = '{0}/p6w'.format((datetime.utcnow() - timedelta(weeks=6)).strftime("%Y-%m-%d"))
        # print(agents)
        for agent in agents:
            group = dral.connection.groupby(
                datasource='supervisor',
                granularity='all',
                intervals=intervals,
                dimensions=["process_name"],
                filter=(Dimension("agent_id") == agent.id),
                aggregations={"count": doublesum("count")})
            # print(type(group.result_json))
            # print(group.result_json)
            data = json.loads(group.result_json)
            processes = {}
            for row in data:
                if row['event']['count'] > 0:
                    processes[row['event']['process_name']] = 'disconnected'
            type(self).AGENTS[agent.name] = processes


scc = SupervisorClientCoordinator()
