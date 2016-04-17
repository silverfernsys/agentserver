#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, with_statement

import json
import tempfile
import time
import unittest
import traceback

from tornado.concurrent import Future
from tornado import gen
from tornado.httpclient import HTTPError, HTTPRequest
from tornado.log import gen_log, app_log
from tornado.testing import AsyncHTTPTestCase, gen_test, bind_unused_port, ExpectLog
from tornado.test.util import unittest
from tornado.web import Application, RequestHandler

try:
    import tornado.websocket  # noqa
    from tornado.util import _websocket_mask_python
except ImportError:
    # The unittest module presents misleading errors on ImportError
    # (it acts as if websocket_test could not be found, hiding the underlying
    # error).  If we get an ImportError here (which could happen due to
    # TORNADO_EXTENSION=1), print some extra information before failing.
    traceback.print_exc()
    raise

from tornado.websocket import WebSocketHandler, websocket_connect, WebSocketError

import sys, os
sys.path.insert(0, os.path.split(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0])[0])

try:
    from tornado import speedups
except ImportError:
    speedups = None

from ws_helpers import websocket_connect
from agentserver.ws import SupervisorAgentHandler, SupervisorStatusHandler, SupervisorCommandHandler
from agentserver.db import dal, User, UserAuthToken, Agent, AgentAuthToken


class TestWebSocketHandler(WebSocketHandler):
    """Base class for testing handlers that exposes the on_close event.
    This allows for deterministic cleanup of the associated socket.
    """
    def initialize(self, close_future, compression_options=None):
        self.close_future = close_future
        self.compression_options = compression_options

    def get_compression_options(self):
        return self.compression_options

    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))


class MockSupervisorAgentHandler(SupervisorAgentHandler, TestWebSocketHandler):
    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))
        super(MockSupervisorAgentHandler, self).on_close()


class MockSupervisorStatusHandler(SupervisorStatusHandler, TestWebSocketHandler):
    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))
        super(MockSupervisorStatusHandler, self).on_close()


class MockSupervisorCommandHandler(SupervisorCommandHandler, TestWebSocketHandler):
    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))
        super(MockSupervisorCommandHandler, self).on_close()


class WebSocketBaseTestCase(AsyncHTTPTestCase):
    @gen.coroutine
    def ws_connect(self, path, headers=None, compression_options=None):
        ws = yield websocket_connect(
            'ws://127.0.0.1:%d%s' % (self.get_http_port(), path), headers=headers,
            compression_options=compression_options)
        raise gen.Return(ws)

    @gen.coroutine
    def close(self, ws):
        """Close a websocket connection and wait for the server side.
        If we don't wait here, there are sometimes leak warnings in the
        tests.
        """
        ws.close()
        yield self.close_future


class WebSocketTest(WebSocketBaseTestCase):
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

        cls.USER_TOKEN = token_0.uuid

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

        cls.AGENT_TOKEN = agent_token_0.uuid
        cls.AGENT_IP = agent_0.ip
        cls.fixtures_dir =  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

    @classmethod
    def tearDownClass(cls):
        dal.session.rollback()
        dal.session.close()

    def get_app(self):
        self.close_future = Future()
        return Application([
            ('/supervisor/', MockSupervisorAgentHandler,
                dict(close_future=self.close_future)),
            ('/cmd/supervisor/', MockSupervisorCommandHandler,
                dict(close_future=self.close_future)),
            ('/status/supervisor/', MockSupervisorStatusHandler,
             dict(close_future=self.close_future)),
        ])

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
        state_web_updates = open(os.path.join(WebSocketTest.fixtures_dir, 'state_web_update.json')).read().split('\n')
        state_celery_updates = open(os.path.join(WebSocketTest.fixtures_dir, 'state_celery_update.json')).read().split('\n')
        snapshot_update_0 = open(os.path.join(WebSocketTest.fixtures_dir, 'snapshot0.json')).read()
        snapshot_update_1 = open(os.path.join(WebSocketTest.fixtures_dir, 'snapshot0.json')).read()

        agent_conn = yield self.ws_connect('/supervisor/',
            headers={'authorization':WebSocketTest.AGENT_TOKEN})
        
        agent = SupervisorAgentHandler.IPConnections[WebSocketTest.AGENT_IP]

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")

        status_conn = yield self.ws_connect('/status/supervisor/',
            headers={'authorization':WebSocketTest.USER_TOKEN})

        cmd_conn = yield self.ws_connect('/cmd/supervisor/',
            headers={'authorization':WebSocketTest.USER_TOKEN})

        # Write a snapshot update and read the response:
        agent_conn.write_message(snapshot_update_0)
        response = yield agent_conn.read_message()
        data = json.loads(response)
        self.assertIn('AQL', data)

        # Write a command to the agent
        cmd_conn.write_message(json.dumps({'cmd': 'restart', 'ip': WebSocketTest.AGENT_IP, 'process': 'web'}))
        # cmd_resp = yield cmd_conn.read_message()
        # print('cmd_resp: %s' % cmd_resp)

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
        cmd_conn.write_message(json.dumps({'cmd': 'restart', 'ip': WebSocketTest.AGENT_IP, 'process': 'celery'}))

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
        yield self.close_future
        self.assertEqual(len(MockSupervisorAgentHandler.Connections), 0, '0 websocket connections.')

if __name__ == '__main__':
    unittest.main()