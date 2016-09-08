# from __future__ import absolute_import
from agentserver.agents.supervisoragent import SupervisorAgent
from agentserver.db.models import Agent
from base import JSONWebsocket


class SupervisorAgentHandler(JSONWebsocket):
    Connections = {}
    IDs = {}

    @classmethod
    def command(cls, id, cmd, process, **kwargs):
        if id in cls.IDs:
            cls.IDs[id].command(cmd, process)
            return True
        return False

    def authorize(self, uuid):
        agent = Agent.authorize(uuid)
        if agent and not (agent.id in self.IDs):
            supervisor_agent = SupervisorAgent(agent.id, self)
            self.IDs[agent.id] = supervisor_agent
            self.Connections[self] = supervisor_agent
            return True
        else:
            return False

    def on_json(self, message):
        """Pass message along to SupervisorAgent if connected,
        ignores message otherwise."""
        if self in self.Connections:
            self.Connections[self].update(message)
        else:
            print('Writing to non-existent agent!')

    def on_close(self):
        try:
            supervisor_agent = self.Connections[self]
            supervisor_agent.ws = None
            self.IDs.pop(supervisor_agent.id, None)
            self.Connections.pop(self, None)
        except:
            pass
