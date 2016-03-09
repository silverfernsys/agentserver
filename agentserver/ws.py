#!/usr/bin/env python
import json
from time import time
import tornado.websocket
from db import dal, UserAuthToken, AgentAuthToken
from agentinfo import AgentInfo


def remote_ip(request):
    return request.headers.get("X-Real-IP") or request.remote_ip


class AgentWSHandler(tornado.websocket.WebSocketHandler):
    Connections = {}

    @classmethod
    def IPs(self):
        return set(remote_ip(c) for c in AgentWSHandler.Connections.keys())

    @tornado.web.addslash
    def open(self):
        """
        Protocol:
        """
        print("AgentWSHandler.open")
        uuid = self.request.headers.get('authorization')
        try:
            token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == uuid).one()
            print('token: %s, uuid: %s' % (token, uuid))
            agent = token.agent
            # AgentWSHandler.Connections[remote_ip(self.request)] = AgentInfo()
            AgentWSHandler.Connections[self] = AgentInfo()
        except Exception as e:
            self.close()
      
    def on_message(self, message):
        """
        We will parse AQL in this method and pass the results on to agent_info.
        """
        # print('AgentWSHandler: message: %s, connections: %s' % (message, AgentWSHandler.Connections))
        # print('AgentWSHandler: connections: %s' % (AgentWSHandler.Connections))
        # ip = remote_ip(self.request)
        if self in AgentWSHandler.Connections:
            try:
                agent_info = AgentWSHandler.Connections[self]
                agent_info.instanceinfo.update(json.loads(message))
                response = {'AQL':'UPDATED AT time=%s' % time()}
                self.write_message(json.dumps(response))
            except Exception as e:
                print('EXCEPTION: %s' % e)
 
    def on_close(self):
        print("AgentWSHandler.on_close")
        # ip = remote_ip(self.request)
        # if ip in AgentWSHandler.Connections:
        AgentWSHandler.Connections.pop(self, None)

    def check_origin(self, origin):
        """
        'Origin' is the base url hit by the request. Eg 10.0.0.10:8081
        """
        return True


class UserWSHandler(tornado.websocket.WebSocketHandler):
    connections = []

    @tornado.web.addslash
    def open(self):
        try:
            uuid = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == uuid).one()
            user = token.user
            UserWSHandler.connections.append(self)
        except Exception as e:
            print('UserWSHandler: Exception Details: %s' % e)
            self.close()
      
    def on_message(self, message):
        print('UserWSHandler: %s' % message)
        # auth_token = self.request.headers.get('authorization')
        # token = Token.tokens().get(token=auth_token)
        # if token and token.user:
        #     data = json.loads(message)
        #     if data['msg'] == 'update':
        #         self.write_message(json.dumps({'msg':'updated'}))
 
    def on_close(self):
        if self in UserWSHandler.connections:
            UserWSHandler.connections.remove(self)

    def check_origin(self, origin):
        return True
