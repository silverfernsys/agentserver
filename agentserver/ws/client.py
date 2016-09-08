# from __future__ import absolute_import
from agentserver.db.models import User
from agentserver.clients.supervisorclient import SupervisorClient
from agentserver.clients.supervisorclientcoordinator import scc
from base import JSONWebsocket


class SupervisorClientHandler(JSONWebsocket):
    Connections = {}

    def authorize(self, uuid):
        user = User.authorize(uuid)
        if user:
            self.Connections[self] = SupervisorClient(user.id, self)
            return True
        else:
            return False

    def on_json(self, message):
        if self in self.Connections:
            self.Connections[self].update(message)
        else:
            print('Writing to non-existent client!')

    def on_close(self):
        try:
            client = self.Connections[self]
            scc.unsubscribe_all(client)
            client.ws = None
            self.Connections.pop(self, None)
        except:
            pass
