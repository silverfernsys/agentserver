#!/usr/bin/env python
import json
from time import time
import tornado.websocket
from db import dal, tal, UserAuthToken, AgentAuthToken
from agents.supervisoragent import SupervisorAgent

SNAPSHOT_UPDATE = 'snapshot_update'
STATE_UPDATE = 'state_update'

def remote_ip(request):
    return request.headers.get("X-Real-IP") or request.remote_ip


class SupervisorAgentHandler(tornado.websocket.WebSocketHandler):
    Connections = {}
    IPConnections = {}

    @classmethod
    def IPs(cls):
        return set(remote_ip(c) for c in SupervisorAgentHandler.Connections.keys())

    @tornado.web.addslash
    def open(self):
        """
        Protocol:
        """
        uuid = self.request.headers.get('authorization')
        if uuid is None:
            self.close()
        else:
            try:
                token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == uuid).one()
                agent = token.agent
                if not (agent.ip in SupervisorAgentHandler.IPConnections):
                    supervisor_agent = SupervisorAgent(agent.ip, agent.timeseries_database_name, self)
                    SupervisorAgentHandler.IPConnections[agent.ip] = supervisor_agent
                    SupervisorAgentHandler.Connections[self] = supervisor_agent
            except Exception as e:
                # print('SupervisorAgentHandler.open EXCEPTION: %s' % e)
                self.close()
      
    def on_message(self, message):
        """
        We will parse AQL in this method and pass the results on to agent_info.
        """
        if self in SupervisorAgentHandler.Connections:
            agent = SupervisorAgentHandler.Connections[self]
            try:
                if message is not None:
                    data = json.loads(message)
                    if STATE_UPDATE in data:
                        agent.state_update(data[STATE_UPDATE])
                        response = {'AQL':'UPDATED AT time=%s' % time()}
                        self.write_message(json.dumps(response))
                        SupervisorStatusHandler.update_state(data[STATE_UPDATE])
                    elif SNAPSHOT_UPDATE in data:
                        # print('data[SNAPSHOT_UPDATE] = %s' % data)
                        agent.snapshot_update(data[SNAPSHOT_UPDATE])
                        response = {'AQL':'UPDATED AT time=%s' % time()}
                        self.write_message(json.dumps(response))
                else:
                    print('MESSAGE IS NONE!! :(')
            except Exception as e:
                print('SupervisorAgentHandler.on_message EXCEPTION 1: %s' % e)
                response = {'AQL':'UPDATED AT time=%s' % time()}
                self.write_message(json.dumps(response))
 
    def on_close(self):
        print("SupervisorAgentHandler.on_close")        
        supervisor_agent = SupervisorAgentHandler.Connections[self]
        supervisor_agent.conn = None
        agent_ip = supervisor_agent.agent_ip
        SupervisorAgentHandler.IPConnections.pop(agent_ip, None)
        SupervisorAgentHandler.Connections.pop(self, None)

    def check_origin(self, origin):
        """
        'Origin' is the base url hit by the request. Eg 10.0.0.10:8081
        """
        return True


class RabbitMQAgentHandler(tornado.websocket.WebSocketHandler):
    Connections = {}
    IPConnections = {}

    @classmethod
    def IPs(self):
        return set(remote_ip(c) for c in RabbitMQAgentHandler.Connections.keys())

    @tornado.web.addslash
    def open(self):
        """
        Protocol:
        """
        pass
      
    def on_message(self, message):
        """
        We will parse AQL in this method and pass the results on to agent_info.
        """
        print(message)
 
    def on_close(self):
        print("AgentWSHandler.on_close")
        AgentWSHandler.Connections.pop(self, None)

    def check_origin(self, origin):
        """
        'Origin' is the base url hit by the request. Eg 10.0.0.10:8081
        """
        return True


class PostgreSQLAgentHandler(tornado.websocket.WebSocketHandler):
    Connections = {}
    IPConnections = {}

    @classmethod
    def IPs(self):
        return set(remote_ip(c) for c in PostgreSQLAgentHandler.Connections.keys())

    @tornado.web.addslash
    def open(self):
        """
        Protocol:
        """
        pass
      
    def on_message(self, message):
        """
        We will parse AQL in this method and pass the results on to agent_info.
        """
        print(message)
 
    def on_close(self):
        print("AgentWSHandler.on_close")
        AgentWSHandler.Connections.pop(self, None)

    def check_origin(self, origin):
        """
        'Origin' is the base url hit by the request. Eg 10.0.0.10:8081
        """
        return True


class SupervisorStatusHandler(tornado.websocket.WebSocketHandler):
    Connections = []

    @tornado.web.addslash
    def open(self):
        print('SupervisorStatusHandler.open()')
        try:
            uuid = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == uuid).one()
            user = token.user
            SupervisorStatusHandler.Connections.append(self)
        except Exception as e:
            print('SupervisorStatusHandler: Exception Details: %s' % e)
            self.close()
      
    def on_message(self, message):
        """
        This function ignores messages from clients.
        """
        pass
 
    def on_close(self):
        if self in SupervisorStatusHandler.Connections:
            SupervisorStatusHandler.Connections.remove(self)

    @classmethod
    def update_state(cls, data):
        for conn in SupervisorStatusHandler.Connections:
            conn.write_message(json.dumps({'cmd':'update'}))

    def check_origin(self, origin):
        return True

class SupervisorCommandHandler(tornado.websocket.WebSocketHandler):
    Connections = []

    @tornado.web.addslash
    def open(self):
        print('SupervisorCommandHandler.open()')
        try:
            uuid = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == uuid).one()
            user = token.user
            SupervisorCommandHandler.Connections.append(self)
        except Exception as e:
            print('SupervisorCommandHandler: Exception Details: %s' % e)
            self.close()
      
    def on_message(self, message):
        """
        This function responds to queries from a client.
        """
        # print('SupervisorCommandHandler.message: %s' % message)
        data = json.loads(message)
        cmd = data['cmd']
        if cmd == 'list_ips':
            response_data = {'ips': SupervisorAgentHandler.IPConnections.keys()}
            self.write_message(json.dumps(response_data))
        elif cmd == 'list_processes':
            try:
                ip = data['ip_address']
                agent = SupervisorAgentHandler.IPConnections[ip]
                is_snapshot = data['snapshot']
                if is_snapshot:
                    data = agent.snapshot()
                else:
                    data = agent.data()
                self.write_message(json.dumps({'processes': data}))
            except Exception as e:
                self.write_message(json.dumps({'error': str(e)}))
        elif cmd in ['start', 'stop', 'restart']:
            try:
                ip = data['ip']
                process = data['process']
                agent = SupervisorAgentHandler.IPConnections[ip]
                # Send command to remote agent! Magic sauce!
                command = {'cmd': '{0} {1}'.format(cmd, process)}
                agent.conn.write_message(json.dumps(command))
                self.write_message(json.dumps({'result': 'success'}))
            except Exception as e:
                self.write_message(json.dumps({'result': 'error', 'details': str(e)}))
        else:
            self.write_message(json.dumps({'error': 'unknown command'}))
 
    def on_close(self):
        if self in SupervisorCommandHandler.Connections:
            SupervisorCommandHandler.Connections.remove(self)

    def check_origin(self, origin):
        return True
