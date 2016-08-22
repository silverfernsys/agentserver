from __future__ import absolute_import, division, print_function, with_statement
from datetime import datetime
import json, mock, os, re, tempfile, time, traceback

from tornado.concurrent import Future
from tornado import gen
from tornado.httpclient import HTTPError, HTTPRequest
from tornado.log import gen_log, app_log
from tornado.testing import AsyncHTTPTestCase, gen_test, bind_unused_port, ExpectLog
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
from db import dal, kal, dral, pal, User, UserAuthToken, Agent, AgentDetail, AgentAuthToken
from utils import validate_timestamp
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
        data = open(os.path.join(FIXTURES_DIR, 'plyql', 'result_{0}.json'.format(agent_id))).read()
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

    @classmethod
    def tearDownClass(cls):
        super(SupervisorAgentHandlerTest, cls).tearDownClass()
        scc.destroy()

    def get_app(self):
        self.close_future = Future()
        return Application([
            ('/supervisor/', MockSupervisorAgentHandler,
                dict(close_future=self.close_future)),
        ])  

    @gen_test
    def test_no_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        ws_client = yield self.ws_connect('/supervisor/')
        ws_client.write_message(json.dumps({'msg':'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because authorization not provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "+0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count, "+0 websocket connections.")

    @gen_test
    def test_bad_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        ws_client = yield self.ws_connect('/supervisor/',
            headers={'authorization':'gibberish'})
        ws_client.write_message(json.dumps({'msg':'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because bad authorization provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "+0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count, "+0 websocket connections.")

    @gen_test
    def test_successful_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        ws_client = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count + 1, "+1 websocket connections.")
        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()), connection_count, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()), id_count, "0 websocket connections.")
    
    @gen_test
    def test_snapshot_update(self):
        update_0 = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_0.json')).read()
        update_1 = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_1.json')).read()

        client = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})
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
        state_0 = open(os.path.join(FIXTURES_DIR, 'states', 'valid_0.json')).read().split('\n')
        state_1 = open(os.path.join(FIXTURES_DIR, 'states', 'valid_1.json')).read().split('\n')

        client = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})

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

        client = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})

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
        state = json.dumps({"state_update":{"group": "celery", "statename": "STOPPING",
            "pid": "8593", "start": 1460513750, "state": 40}})

        client = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})

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
    def test_system_stats(self):
        stats = json.dumps({'system_stats': {'dist_name': 'Ubuntu',
            'dist_version': '15.10', 'hostname': 'client', 'num_cores': 3,
            'memory': 1040834560, 'processor': 'x86_64'}})

        agent = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})

        agent.write_message(stats)
        response = yield agent.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'system stats updated')

        # missing num_cores
        incomplete_stats = json.dumps({'system_stats': {'dist_name': 'Ubuntu',
            'dist_version': '15.10', 'hostname': 'client',
            'memory': 1040834560, 'processor': 'x86_64'}})
        agent.write_message(incomplete_stats)
        response = yield agent.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        agent.close()
        yield self.close_future


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
    @mock.patch('db.pal.query', side_effect=pal_mock_query)
    def setUpClass(cls, mock_query):
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

        agent = Agent(name='Agent 0')
        dal.session.add(AgentAuthToken(agent=agent))
        dal.session.commit()
        dral.connect('debug')
        pal.connect('debug')
        scc.initialize()
        print(scc)

        cls.AGENT_TOKEN = agent.token.uuid
        cls.AGENT_ID = agent.id
        cls.USER_TOKEN = user.token.uuid

    @classmethod
    def tearDownClass(cls):
        super(SupervisorClientHandlerTest, cls).tearDownClass()
        scc.destroy()

    def get_app(self):
        self.close_future = Future()
        return Application([
            ('/supervisor/', MockSupervisorAgentHandler,
                dict(close_future=self.close_future)),
            ('/client/supervisor/', MockSupervisorClientHandler,
                dict(close_future=self.close_future)),
        ]) 

    @gen_test
    def test_no_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield self.ws_connect('/client/supervisor/')
        ws_client.write_message(json.dumps({'cmd':'restart'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because authorization not provided.")
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "+0 websocket connections.")

    @gen_test
    def test_bad_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield self.ws_connect('/client/supervisor/',
            headers={'authorization':'gibberish'})
        ws_client.write_message(json.dumps({'cmd':'restart'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because bad authorization provided.")
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "+0 websocket connections.")

    @gen_test
    def test_successful_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield self.ws_connect('/client/supervisor/',
            headers={'authorization': self.USER_TOKEN})
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")
        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "0 websocket connections.")

    @gen_test
    def test_cmd_success(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield self.ws_connect('/client/supervisor/',
            headers={'authorization': self.USER_TOKEN})
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")
        
        ws_agent = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN})

        ws_client.write_message(json.dumps({'cmd': 'sub', 'id': self.AGENT_ID, 'process': 'process_0'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command sub accepted')

        response = yield ws_client.read_message()
        data = json.loads(response)['snapshot_update']
        self.assertEqual(data['process'], 'process_0')
        self.assertEqual(data['id'], self.AGENT_ID)
        for stat in data['stats']:
            self.assertTrue(validate_timestamp(stat['timestamp']))
            self.assertTrue(type(stat['cpu']) == float)
            self.assertTrue(type(stat['mem']) == int)

        yield ws_client.write_message(json.dumps({'cmd': 'restart', 'id': self.AGENT_ID, 'process': 'process_0'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command restart accepted')

        response = yield ws_agent.read_message()
        data = json.loads(response)
        self.assertEqual(data['cmd'], 'restart process_0')

        state_0 = open(os.path.join(FIXTURES_DIR, 'states', 'valid_0.json')).read().split('\n')

        for state in state_0:
            ws_agent.write_message(state)
            response = yield ws_agent.read_message()
            data = json.loads(response)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['type'], 'state updated')

        for state in state_0:
            response = yield ws_client.read_message()
            data = json.loads(response)['state_update']
            sent_data = json.loads(state)['state_update']
            self.assertEqual(sent_data['name'], data['name'])
            self.assertEqual(sent_data['statename'], data['state'])
            self.assertEqual(datetime.utcfromtimestamp(sent_data['start']). \
                strftime("%Y-%m-%dT%H:%M:%S.%fZ"), data['started'])

        # Wait for another message sent from scc to the client
        response = yield ws_client.read_message()
        data = json.loads(response)['snapshot_update']
        self.assertEqual(data['process'], 'process_0')
        self.assertEqual(data['id'], self.AGENT_ID)
        for stat in data['stats']:
            self.assertTrue(validate_timestamp(stat['timestamp']))
            self.assertTrue(type(stat['cpu']) == float)
            self.assertTrue(type(stat['mem']) == int)

        ws_client.write_message(json.dumps({'cmd': 'unsub', 'id': self.AGENT_ID, 'process': 'process_0'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command unsub accepted')

        ws_client.write_message(json.dumps({'cmd': 'sub', 'id': self.AGENT_ID, 'process': 'process_1'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command sub accepted')

        response = yield ws_client.read_message()
        data = json.loads(response)['snapshot_update']
        self.assertEqual(data['process'], 'process_1')
        self.assertEqual(data['id'], self.AGENT_ID)
        for stat in data['stats']:
            self.assertTrue(validate_timestamp(stat['timestamp']))
            self.assertTrue(type(stat['cpu']) == float)
            self.assertTrue(type(stat['mem']) == int)

        yield ws_client.write_message(json.dumps({'cmd': 'restart', 'id': self.AGENT_ID, 'process': 'process_1'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['type'], 'command restart accepted')

        response = yield ws_agent.read_message()
        data = json.loads(response)
        self.assertEqual(data['cmd'], 'restart process_1')

        state_1 = open(os.path.join(FIXTURES_DIR, 'states', 'valid_1.json')).read().split('\n')

        for state in state_1:
            ws_agent.write_message(state)
            response = yield ws_agent.read_message()
            data = json.loads(response)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['type'], 'state updated')

        for state in state_1:
            response = yield ws_client.read_message()
            data = json.loads(response)['state_update']
            sent_data = json.loads(state)['state_update']
            self.assertEqual(sent_data['name'], data['name'])
            self.assertEqual(sent_data['statename'], data['state'])
            self.assertEqual(datetime.utcfromtimestamp(sent_data['start']). \
                strftime("%Y-%m-%dT%H:%M:%S.%fZ"), data['started'])

        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "0 websocket connections.")

        ws_agent.close()
        yield self.close_future
        time.sleep(1.0)

    @gen_test
    def test_cmd_failure(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        ws_client = yield self.ws_connect('/client/supervisor/',
            headers={'authorization': self.USER_TOKEN})
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count + 1, "+1 websocket connections.")

        ws_client.write_message(json.dumps({'cmd': 'restart', 'id': 100, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'agent not connected')

        ws_client.write_message(json.dumps({'id': self.AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'cmd': 'restart', 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'cmd': 'restart', 'id': self.AGENT_ID}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown message type')

        ws_client.write_message(json.dumps({'cmd': 'unknown', 'id': self.AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        data = json.loads(response)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['type'], 'unknown command')

        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()), connection_count, "0 websocket connections.")
