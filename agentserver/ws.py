#!/usr/bin/env python
import json
from time import time
import tornado.websocket
from db import Agent, User 
from agents.supervisoragent import SupervisorAgent
from clients.supervisorclient import SupervisorClient
from clients.supervisorclientcoordinator import scc


class JSONWebsocket(tornado.websocket.WebSocketHandler):
    invalid_json_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid json'}]})

    def authorize(self, uuid):
        """Override this method."""
        raise NotImplementedError

    def on_json(self, message):
        """Override this method."""
        raise NotImplementedError

    def open(self):
        uuid = self.request.headers.get('authorization')
        if uuid is None or not self.authorize(uuid):
            self.close()

    def on_message(self, message):
        try:
            data = tornado.escape.json_decode(message)
            self.on_json(data)
        except:
            self.write_message(self.invalid_json_error)

    def check_origin(self, origin):
        return True


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
