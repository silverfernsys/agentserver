#!/usr/bin/env python
import json
from time import time
import tornado.websocket
from db import dal, kal, UserAuthToken, AgentAuthToken
from sqlalchemy.orm.exc import NoResultFound
from agents.supervisoragent import SupervisorAgent
from clients.supervisorclient import SupervisorClient
from clients.supervisorclientcoordinator import scc

class SupervisorAgentHandler(tornado.websocket.WebSocketHandler):
    Connections = {}
    IDs = {}

    @tornado.web.addslash
    def open(self):
        uuid = self.request.headers.get('authorization')
        if uuid is None:
            self.close()
        else:
            try:
                token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == uuid).one()
                agent = token.agent
                if not (agent.id in SupervisorAgentHandler.IDs):
                    supervisor_agent = SupervisorAgent(agent.id, self)
                    SupervisorAgentHandler.IDs[agent.id] = supervisor_agent
                    SupervisorAgentHandler.Connections[self] = supervisor_agent
                else:
                    self.close()
            except NoResultFound:
                self.close()
            except Exception as e:
                self.close()
      
    def on_message(self, message):
        """Pass message along to SupervisorAgent if connected,
        ignores message otherwise."""
        if self in SupervisorAgentHandler.Connections:
            SupervisorAgentHandler.Connections[self].update(message)
        else:
            print('Writing to non-existent agent!')
 
    def on_close(self):
        try:   
            supervisor_agent = SupervisorAgentHandler.Connections[self]
            supervisor_agent.ws = None
            SupervisorAgentHandler.IDs.pop(supervisor_agent.id, None)
            SupervisorAgentHandler.Connections.pop(self, None)
        except:
            pass

    def check_origin(self, origin):
        """'origin' is the base url hit by the request.
        Eg 10.0.0.10:8081"""
        return True


class SupervisorClientHandler(tornado.websocket.WebSocketHandler):
    Connections = {}

    @tornado.web.addslash
    def open(self):
        uuid = self.request.headers.get('authorization')
        if uuid is None:
            self.close()
        else:
            try:
                token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == uuid).one()
                SupervisorClientHandler.Connections[self] = SupervisorClient(token.user.id, self)
            except NoResultFound:
                self.close()
            except Exception:
                self.close()

    def on_message(self, message):
        if self in SupervisorClientHandler.Connections:
            SupervisorClientHandler.Connections[self].update(message)
        else:
            print('Writing to non-existent client!')

    def on_close(self):
        try:
            client = SupervisorClientHandler.Connections[self]
            scc.unsubscribe_all(client)
            client.ws = None
            SupervisorClientHandler.Connections.pop(self, None)
        except:
            pass

    def check_origin(self, origin):
        return True
