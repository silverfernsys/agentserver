from __future__ import absolute_import, division, print_function, with_statement

import json, mock, os, re, tempfile, time, traceback

from tornado.concurrent import Future
from tornado import gen
from tornado.httpclient import HTTPError, HTTPRequest
from tornado.log import gen_log, app_log
from tornado.testing import AsyncHTTPTestCase, gen_test, bind_unused_port, ExpectLog
# from tornado.test.util import unittest
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

try:
    from tornado import speedups
except ImportError:
    speedups = None

from ws_helpers import websocket_connect
from ws import SupervisorAgentHandler, SupervisorClientHandler
from db import dal, kal, dral, pal, User, UserAuthToken, Agent, AgentAuthToken
from clients.supervisorclientcoordinator import scc


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


class MockSupervisorClientHandler(SupervisorClientHandler, TestWebSocketHandler):
    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))
        super(MockSupervisorClientHandler, self).on_close()


class WebSocketBaseTestCase(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')
        dal.session = dal.Session()
        kal.connect('debug')

    @classmethod
    def tearDownClass(cls):
        dal.session.rollback()
        dal.session.close()

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
        tests."""
        ws.close()
        yield self.close_future


FIXTURES_DIR =  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')


def pal_mock_query(q, interval=None):
    try:
        agent_id = re.search(r'agent_id = "(.+?)"', q).group(1)
        data = open(os.path.join(FIXTURES_DIR, 'plyql{0}.json'.format(agent_id))).read()
        return data
    except (AttributeError, IOError):
        return '[]'


class SupervisorAgentHandlerTest(WebSocketBaseTestCase):
    @classmethod
    @mock.patch('db.pal.query', side_effect=pal_mock_query)
    def setUpClass(cls, mock_query):
        super(SupervisorAgentHandlerTest, cls).setUpClass()
        # Generate agents
        agent = Agent(name='Agent 0')
        dal.session.add_all([AgentAuthToken(agent=agent),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2'))])
        dal.session.commit()
        dral.connect('debug')
        pal.connect('debug')
        scc.initialize()

        cls.AGENT_TOKEN = agent.token.uuid
        cls.AGENT_ID = agent.id

    def get_app(self):
        self.close_future = Future()
        return Application([
            ('/supervisor/', MockSupervisorAgentHandler,
                dict(close_future=self.close_future)),
            # ('/cmd/supervisor/', MockSupervisorCommandHandler,
            #     dict(close_future=self.close_future)),
            # ('/status/supervisor/', MockSupervisorStatusHandler,
            #  dict(close_future=self.close_future)),
        ])

    def url(self):
        return 'ws://localhost:' + str(self.get_http_port()) + '/supervisor/'  

    @gen_test
    def test_no_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        ws_client = yield websocket_connect(self.url())
        # print(dir(ws_client))
        ws_client.write_message(json.dumps({'msg':'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because authorization not provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "+0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count, "+0 websocket connections.")

    @gen_test
    def test_bad_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        ws_client = yield websocket_connect(self.url(), headers={'authorization':'gibberish'})
        ws_client.write_message(json.dumps({'msg':'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because bad authorization provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "+0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count, "+0 websocket connections.")

    @gen_test
    def test_successful_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        ws_client = yield websocket_connect(self.url(), headers={'authorization': type(self).AGENT_TOKEN})
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count + 1, "+1 websocket connections.")
        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count, "0 websocket connections.")
    
    @gen_test
    def test_snapshot_update(self):
        update_0 = open(os.path.join(FIXTURES_DIR, 'snapshot0.json')).read()
        update_1 = open(os.path.join(FIXTURES_DIR, 'snapshot1.json')).read()

        client = yield websocket_connect(self.url(), headers={'authorization': type(self).AGENT_TOKEN})
        client.write_message(update_0)
        response = yield client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'snapshot updated')

        client.write_message(update_1)
        response = yield client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'snapshot updated')

        client.write_message('malformed json')
        response = yield client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), 0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), 0, "0 websocket connections.")

    @gen_test
    def test_state_update(self):
        state_0 = open(os.path.join(FIXTURES_DIR, 'state0.json')).read().split('\n')
        state_1 = open(os.path.join(FIXTURES_DIR, 'state1.json')).read().split('\n')

        client = yield websocket_connect(self.url(), headers={'authorization': type(self).AGENT_TOKEN})

        for state in state_0:
            client.write_message(state)
            response = yield client.read_message()
            data = json.loads(response)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['type'], 'state updated')

        for state in state_1:
            client.write_message(state)
            response = yield client.read_message()
            data = json.loads(response)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['type'], 'state updated')

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), 0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), 0, "0 websocket connections.")

    @gen_test
    def test_state_update_bad_start_value(self):
        state = json.dumps({"state_update":{"group": "celery", "name": "celery", "statename": "STOPPING", "pid": "8593", "start": 'asdf', "state": 40}})

        client = yield websocket_connect(self.url(), headers={'authorization': type(self).AGENT_TOKEN})

        client.write_message(state)
        response = yield client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), 0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), 0, "0 websocket connections.")

    @gen_test
    def test_state_update_missing_values(self):
        state = json.dumps({"state_update":{"group": "celery", "statename": "STOPPING", "pid": "8593", "start": 1460513750, "state": 40}})

        client = yield websocket_connect(self.url(), headers={'authorization': type(self).AGENT_TOKEN})

        client.write_message(state)
        response = yield client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), 0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), 0, "0 websocket connections.")


class SupervisorAgentMock(object):
    def __init__(self, id, ip):
        self.id = id
        self.ip = ip
        self.session = dal.Session()
        self.processes = {}

    def update(self, message):
        pass

class SupervisorClientHandlerTest(WebSocketBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(SupervisorClientHandlerTest, cls).setUpClass()
        # Generate users and tokens
        user = User(name='User A',
                         email='user_a@example.com',
                         is_admin=True,
                         password='randompassworda')
        dal.session.add_all([UserAuthToken(user=user),
            UserAuthToken(user=User(name='User B',
                     email='user_b@example.com',
                     is_admin=False,
                     password='randompasswordb')),
            UserAuthToken(user=User(name='User C',
                     email='user_c@example.com',
                     is_admin=True,
                     password='randompasswordc'))])
        dal.session.commit()

        cls.USER_TOKEN = user.token.uuid
        cls.AGENT_ID = 1

    def get_app(self):
        self.close_future = Future()
        return Application([
            ('/client/supervisor/', MockSupervisorClientHandler,
                dict(close_future=self.close_future)),
        ])

    def url(self):
        return 'ws://localhost:' + str(self.get_http_port()) + '/client/supervisor/'  

    @gen_test
    def test_no_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield websocket_connect(self.url())
        ws_client.write_message(json.dumps({'cmd':'restart'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because authorization not provided.")
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "+0 websocket connections.")

    @gen_test
    def test_bad_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield websocket_connect(self.url(), headers={'authorization':'gibberish'})
        ws_client.write_message(json.dumps({'cmd':'restart'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because bad authorization provided.")
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "+0 websocket connections.")

    @gen_test
    def test_successful_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield websocket_connect(self.url(), headers={'authorization': type(self).USER_TOKEN})
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")
        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "0 websocket connections.")

    @gen_test
    def test_cmd_success(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield websocket_connect(self.url(), headers={'authorization': type(self).USER_TOKEN})
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")
        
        ws_client.write_message(json.dumps({'cmd': 'restart', 'id': type(self).AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command restart accepted')

        ws_client.write_message(json.dumps({'cmd': 'follow', 'id': type(self).AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command follow accepted')

        # try:
        #     response = yield ws_client.read_message()
        # except Exception as e:
        #     print(e)

        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "0 websocket connections.")

    @gen_test
    def test_cmd_failure(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield websocket_connect(self.url(), headers={'authorization': type(self).USER_TOKEN})
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")

        # ws_client.write_message(json.dumps({'cmd': 'restart', 'id': 100, 'process': 'web'}))
        # response = yield ws_client.read_message()
        # data = json.loads(response)
        # self.assertEqual(data['status'], 'error')
        # self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'id': type(self).AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'cmd': 'restart', 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'cmd': 'restart', 'id': type(self).AGENT_ID}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'cmd': 'unknown', 'id': type(self).AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "0 websocket connections.")

    # @gen_test
    # def test_supervisoragenthandler_state_update(self):
    #     connection_count = len(SupervisorAgentHandler.Connections.keys())
    #     state_web_updates = open(os.path.join(WebSocketTest.fixtures_dir, 'state_web_update.json')).read().split('\n')
    #     state_celery_updates = open(os.path.join(WebSocketTest.fixtures_dir, 'state_celery_update.json')).read().split('\n')
    #     snapshot_update_0 = open(os.path.join(WebSocketTest.fixtures_dir, 'snapshot0.json')).read()
    #     snapshot_update_1 = open(os.path.join(WebSocketTest.fixtures_dir, 'snapshot1.json')).read()

    #     agent_conn = yield self.ws_connect('/supervisor/',
    #         headers={'authorization':WebSocketTest.AGENT_TOKEN})
        
    #     # agent = SupervisorAgentHandler.IPConnections[WebSocketTest.AGENT_IP]

    #     self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")

    #     status_conn = yield self.ws_connect('/status/supervisor/',
    #         headers={'authorization':WebSocketTest.USER_TOKEN})

    #     cmd_conn = yield self.ws_connect('/cmd/supervisor/',
    #         headers={'authorization':WebSocketTest.USER_TOKEN})

    #     # Write a snapshot update and read the response:
    #     agent_conn.write_message(snapshot_update_0)
    #     response = yield agent_conn.read_message()
    #     data = json.loads(response)
    #     self.assertIn('AQL', data)

    #     # Write a command to the agent
    #     cmd_conn.write_message(json.dumps({'cmd': 'restart', 'ip': WebSocketTest.AGENT_IP, 'process': 'web'}))
    #     # cmd_resp = yield cmd_conn.read_message()
    #     # print('cmd_resp: %s' % cmd_resp)

    #     # Read the command sent to the agent
    #     response = yield agent_conn.read_message()
    #     command = json.loads(response)
    #     self.assertIn('cmd', command)
    #     self.assertEqual(command['cmd'], 'restart web')

    #     # Write state updates of web process restarting:
    #     for state_web_update in state_web_updates:
    #         agent_conn.write_message(state_web_update)
    #         response = yield agent_conn.read_message()
    #         data = json.loads(response)
    #         self.assertIn('AQL', data)

    #     process_info_web = agent.get('web', 'web')
    #     self.assertEqual(8, len(process_info_web.cpu), '8 cpu datapoints')
    #     self.assertEqual(8, len(process_info_web.mem), '8 mem datapoints')

    #     # Write a command to the agent
    #     cmd_conn.write_message(json.dumps({'cmd': 'restart', 'ip': WebSocketTest.AGENT_IP, 'process': 'celery'}))

    #     # Read the command sent to the agent
    #     response = yield agent_conn.read_message()
    #     command = json.loads(response)
    #     self.assertIn('cmd', command)
    #     self.assertEqual(command['cmd'], 'restart celery')

    #     # Write state updates of celery process restarting:
    #     for state_celery_update in state_celery_updates:
    #         agent_conn.write_message(state_celery_update)
    #         response = yield agent_conn.read_message()
    #         data = json.loads(response)
    #         self.assertIn('AQL', data)

    #     # Read updates from status connection:
    #     for i in range(len(state_web_updates) + len(state_celery_updates)):
    #         response = yield status_conn.read_message()
    #         data = json.loads(response)
    #         self.assertIn('cmd', data)
    #         self.assertEqual(data['cmd'], 'update')

    #     # Write a snapshot update and read the response:
    #     agent_conn.write_message(snapshot_update_1)
    #     response = yield agent_conn.read_message()
    #     data = json.loads(response)
    #     self.assertIn('AQL', data)
    #     self.assertEqual(16, len(process_info_web.cpu), '16 cpu datapoints')
    #     self.assertEqual(16, len(process_info_web.mem), '16 mem datapoints')

    #     agent_conn.close()
    #     yield self.close_future
    #     self.assertEqual(len(MockSupervisorAgentHandler.Connections), 0, '0 websocket connections.')
