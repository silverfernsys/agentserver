#!/usr/bin/env python
import json
from time import time
import tornado.websocket
from db import dal, kal, UserAuthToken, AgentAuthToken
from sqlalchemy.orm.exc import NoResultFound
from agents.supervisoragent import SupervisorAgent


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
        ignores message otherwise.
        """
        if self in SupervisorAgentHandler.Connections:
            SupervisorAgentHandler.Connections[self].update(message)
        else:
            print('Writing to non-existent agent!')
 
    def on_close(self):       
        supervisor_agent = SupervisorAgentHandler.Connections[self]
        supervisor_agent.ws = None
        SupervisorAgentHandler.IDs.pop(supervisor_agent.id, None)
        SupervisorAgentHandler.Connections.pop(self, None)

    def check_origin(self, origin):
        """'origin' is the base url hit by the request.
        Eg 10.0.0.10:8081
        """
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
        pass

    def on_close(self):
        client = SupervisorClientHandler.Connections[self]
        client.ws = None
        SupervisorClientHandler.Connections.pop(self, None)

    def check_origin(self, origin):
        return True

# class SupervisorStatusHandler(tornado.websocket.WebSocketHandler):
#     Connections = []

#     @tornado.web.addslash
#     def open(self):
#         print('SupervisorStatusHandler.open()')
#         try:
#             uuid = self.request.headers.get('authorization')
#             token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == uuid).one()
#             user = token.user
#             SupervisorStatusHandler.Connections.append(self)
#         except Exception as e:
#             print('SupervisorStatusHandler: Exception Details: %s' % e)
#             self.close()
      
#     def on_message(self, message):
#         """
#         This function ignores messages from clients.
#         """
#         pass
 
#     def on_close(self):
#         if self in SupervisorStatusHandler.Connections:
#             SupervisorStatusHandler.Connections.remove(self)

#     @classmethod
#     def update_state(cls, data):
#         for conn in SupervisorStatusHandler.Connections:
#             conn.write_message(json.dumps({'cmd':'update'}))

#     def check_origin(self, origin):
#         return True

# class SupervisorCommandHandler(tornado.websocket.WebSocketHandler):
#     Connections = []

#     @tornado.web.addslash
#     def open(self):
#         print('SupervisorCommandHandler.open()')
#         try:
#             uuid = self.request.headers.get('authorization')
#             token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == uuid).one()
#             user = token.user
#             SupervisorCommandHandler.Connections.append(self)
#         except Exception as e:
#             print('SupervisorCommandHandler: Exception Details: %s' % e)
#             self.close()
      
#     def on_message(self, message):
#         print('SupervisorCommandHandler.on_message')
#         """
#         This function responds to queries from a client.
#         """
#         # print('SupervisorCommandHandler.message: %s' % message)
#         data = json.loads(message)
#         cmd = data['cmd']
#         if cmd == 'list_ips':
#             response_data = {'ips': SupervisorAgentHandler.IPConnections.keys()}
#             self.write_message(json.dumps(response_data))
#         elif cmd == 'list_processes':
#             try:
#                 ip = data['ip_address']
#                 agent = SupervisorAgentHandler.IPConnections[ip]
#                 is_snapshot = data['snapshot']
#                 if is_snapshot:
#                     data = agent.snapshot()
#                 else:
#                     data = agent.data()
#                 self.write_message(json.dumps({'processes': data}))
#             except Exception as e:
#                 self.write_message(json.dumps({'error': str(e)}))
#         elif cmd in ['start', 'stop', 'restart']:
#             print('INSIDE START STOP RESTART!!!')
#             try:
#                 ip = data['ip']
#                 process = data['process']
#                 agent = SupervisorAgentHandler.IPConnections[ip]
#                 # Send command to remote agent! Magic sauce!
#                 command = {'cmd': '{0} {1}'.format(cmd, process)}
#                 agent.conn.write_message(json.dumps(command))
#                 self.write_message(json.dumps({'result': 'success'}))
#             except Exception as e:
#                 self.write_message(json.dumps({'result': 'error', 'details': str(e)}))
#         else:
#             self.write_message(json.dumps({'error': 'unknown command'}))
 
#     def on_close(self):
#         if self in SupervisorCommandHandler.Connections:
#             SupervisorCommandHandler.Connections.remove(self)

#     def check_origin(self, origin):
#         return True
