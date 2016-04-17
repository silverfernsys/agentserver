#!/usr/bin/env python
# http://stackoverflow.com/questions/9336080/how-do-you-use-tornado-testing-for-creating-websocket-unit-tests
import json
import tempfile
import time
import unittest

from tornado.concurrent import Future
from tornado import simple_httpclient, httpclient
from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop
from tornado.tcpclient import TCPClient
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application
from tornado.websocket import WebSocketProtocol13

import sys, os
sys.path.insert(0, os.path.split(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0])[0])

from ws_helpers import websocket_connect
from agentserver.ws import SupervisorAgentHandler, SupervisorStatusHandler, SupervisorCommandHandler
from agentserver.db import dal, User, UserAuthToken, Agent, AgentAuthToken


class WebSocketTestCase(AsyncHTTPTestCase):
    USER_TOKEN = None
    AGENT_TOKEN = None
    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')
        dal.session = dal.Session()

        # Generate users
        user_0 = User(name='Marc Wilson',
                         email='marcw@silverfern.io',
                         is_admin=True,
                         password='asdf')
        user_1 = User(name='Phil Lake',
                         email='philip@gmail.com',
                         is_admin=False,
                         password='asdf')
        user_2 = User(name='Colin Ng',
                         email='colin@ngland.net',
                         is_admin=True,
                         password='asdf')

        # Generate user tokens
        token_0 = UserAuthToken(user=user_0)
        token_1 = UserAuthToken(user=user_1)
        token_2 = UserAuthToken(user=user_2)
        dal.session.add(token_0)
        dal.session.add(token_1)
        dal.session.add(token_2)
        dal.session.commit()

        WebSocketTestCase.USER_TOKEN = token_0.uuid

        # Generate agents
        agent_0 = Agent(ip='192.168.10.12', retention_policy='5d', timeseries_database_name='timeseries1')
        agent_1 = Agent(ip='192.168.10.13', retention_policy='1w', timeseries_database_name='timeseries2')
        agent_2 = Agent(ip='192.168.10.14', retention_policy='INF', timeseries_database_name='timeseries3')
        # dal.session.bulk_save_objects([agent_0, agent_1, agent_2])
        # dal.session.commit()

        agent_token_0 = AgentAuthToken(agent=agent_0)
        agent_token_1 = AgentAuthToken(agent=agent_1)
        agent_token_2 = AgentAuthToken(agent=agent_2)
        dal.session.add(agent_token_0)
        dal.session.add(agent_token_1)
        dal.session.add(agent_token_2)
        dal.session.commit()

        WebSocketTestCase.AGENT_TOKEN = agent_token_0.uuid
        WebSocketTestCase.AGENT_IP = agent_0.ip

        WebSocketTestCase.fixtures_dir =  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

    @classmethod
    def tearDownClass(cls):
        dal.session.rollback()
        dal.session.close()

    def get_app(self):
        self.close_future = Future()
        app = Application([
            # Agents
            (r'/supervisor/', SupervisorAgentHandler), #, dict(close_future=self.close_future)),
            # Commands and Status handlers
            (r'/cmd/supervisor/', SupervisorCommandHandler), #dict(close_future=self.close_future)),
            (r'/status/supervisor/', SupervisorStatusHandler), #dict(close_future=self.close_future)),
        ])
        return app

    @gen_test
    def test_supervisoragenthandler_no_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        ws_url = 'ws://localhost:' + str(self.get_http_port()) + '/supervisor/'
        ws_client = yield websocket_connect(ws_url)
        ws_client.write_message(json.dumps({'msg':'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because authorization not provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "+0 websocket connections.")

    @gen_test
    def test_supervisoragenthandler_bad_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        ws_url = 'ws://localhost:' + str(self.get_http_port()) + '/supervisor/'
        ws_client = yield websocket_connect(ws_url, headers={'authorization':'asdf'})
        ws_client.write_message(json.dumps({'msg':'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because bad authorization provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "+0 websocket connections.")

    @gen_test
    def test_supervisoragenthandler_state_update(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        state_web_updates = open(os.path.join(WebSocketTestCase.fixtures_dir, 'state_web_update.json')).read().split('\n')
        state_celery_updates = open(os.path.join(WebSocketTestCase.fixtures_dir, 'state_celery_update.json')).read().split('\n')
        snapshot_update_0 = open(os.path.join(WebSocketTestCase.fixtures_dir, 'snapshot0.json')).read()
        snapshot_update_1 = open(os.path.join(WebSocketTestCase.fixtures_dir, 'snapshot0.json')).read()

        agent_conn = yield websocket_connect('ws://localhost:' + str(self.get_http_port()) + '/supervisor/',
            headers={'authorization':WebSocketTestCase.AGENT_TOKEN})
        
        agent = SupervisorAgentHandler.IPConnections[WebSocketTestCase.AGENT_IP]

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")

        status_conn = yield websocket_connect('ws://localhost:' + str(self.get_http_port()) + '/status/supervisor/',
            headers={'authorization':WebSocketTestCase.USER_TOKEN})

        cmd_conn = yield websocket_connect('ws://localhost:' + str(self.get_http_port()) + '/cmd/supervisor/',
            headers={'authorization':WebSocketTestCase.USER_TOKEN})

        # Write a snapshot update and read the response:
        agent_conn.write_message(snapshot_update_0)
        response = yield agent_conn.read_message()
        data = json.loads(response)
        self.assertIn('AQL', data)

        # Write a command to the agent
        cmd_conn.write_message(json.dumps({'cmd': 'restart', 'ip': WebSocketTestCase.AGENT_IP, 'process': 'web'}))

        # Read the command sent to the agent
        response = yield agent_conn.read_message()
        command = json.loads(response)
        self.assertIn('cmd', command)
        self.assertEqual(command['cmd'], 'restart web')

        # Write state updates of web process restarting:
        for state_web_update in state_web_updates:
            agent_conn.write_message(state_web_update)
            response = yield agent_conn.read_message()
            data = json.loads(response)
            self.assertIn('AQL', data)

        process_info_web = agent.get('web', 'web')
        self.assertEqual(8, len(process_info_web.cpu), '8 cpu datapoints')
        self.assertEqual(8, len(process_info_web.mem), '8 mem datapoints')

        # Write a command to the agent
        cmd_conn.write_message(json.dumps({'cmd': 'restart', 'ip': WebSocketTestCase.AGENT_IP, 'process': 'celery'}))

        # Read the command sent to the agent
        response = yield agent_conn.read_message()
        command = json.loads(response)
        self.assertIn('cmd', command)
        self.assertEqual(command['cmd'], 'restart celery')

        # Write state updates of celery process restarting:
        for state_celery_update in state_celery_updates:
            agent_conn.write_message(state_celery_update)
            response = yield agent_conn.read_message()
            data = json.loads(response)
            self.assertIn('AQL', data)

        # Read updates from status connection:
        for i in range(len(state_web_updates) + len(state_celery_updates)):
            response = yield status_conn.read_message()
            data = json.loads(response)
            self.assertIn('cmd', data)
            self.assertEqual(data['cmd'], 'update')

        # Write a snapshot update and read the response:
        agent_conn.write_message(snapshot_update_1)
        response = yield agent_conn.read_message()
        data = json.loads(response)
        self.assertIn('AQL', data)
        self.assertEqual(16, len(process_info_web.cpu), '16 cpu datapoints')
        self.assertEqual(16, len(process_info_web.mem), '16 mem datapoints')

        agent_conn.close()
        # yield self.close_future

if __name__ == '__main__':
    unittest.main()