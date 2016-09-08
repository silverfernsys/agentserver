from __future__ import (absolute_import, division,
                        print_function, with_statement)
from datetime import datetime
import json
import os
import time
import traceback

from tornado import gen
from tornado.concurrent import Future
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase, gen_test

try:
    import tornado.websocket  # noqa
except ImportError:
    # The unittest module presents misleading errors on ImportError
    # (it acts as if websocket_test could not be found, hiding the underlying
    # error).  If we get an ImportError here (which could happen due to
    # TORNADO_EXTENSION=1), print some extra information before failing.
    traceback.print_exc()
    raise

try:
    from tornado import speedups
except ImportError:
    speedups = None

from mocks.timeseries import KafkaProducerMock, PyDruidMock, PlyQLMock
from ws_helpers import websocket_connect
from agentserver.ws.agent import SupervisorAgentHandler
from agentserver.ws.client import SupervisorClientHandler
from agentserver.db.models import models, User, UserAuthToken, Agent, AgentAuthToken
from agentserver.db.timeseries import kafka, druid
from agentserver.utils import validators
from agentserver.clients.supervisorclient import SupervisorClient
from agentserver.clients.supervisorclientcoordinator import scc
from agentserver.agents.supervisoragent import SupervisorAgent
from ws_helpers import MockSupervisorAgentHandler, MockSupervisorClientHandler


resources = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), 'resources')


class WebSocketBaseTestCase(AsyncHTTPTestCase):

    @classmethod
    def setUpClass(cls):
        models.connect('sqlite:///:memory:')
        kafka.connection = KafkaProducerMock()
        # kafka.connect('debug')

    @classmethod
    def tearDownClass(cls):
        models.session.rollback()
        models.session.close()

    @gen.coroutine
    def ws_connect(self, path, headers=None, compression_options=None):
        ws = yield websocket_connect(
            'ws://127.0.0.1:%d%s' % (self.get_http_port(), path),
            headers=headers, compression_options=compression_options)
        raise gen.Return(ws)

    @gen.coroutine
    def close(self, ws):
        """Close a websocket connection and wait for the server side.
        If we don't wait here, there are sometimes leak warnings in the
        tests."""
        ws.close()
        yield self.close_future


class SupervisorAgentHandlerTest(WebSocketBaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(SupervisorAgentHandlerTest, cls).setUpClass()
        # Generate agents
        agent = Agent(name='Agent 0')
        models.session.add_all([AgentAuthToken(agent=agent),
                                AgentAuthToken(agent=Agent(name='Agent 1')),
                                AgentAuthToken(agent=Agent(name='Agent 2'))])
        models.session.commit()
        druid.connection = PyDruidMock()
        druid.plyql = PlyQLMock()
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
        ws_client.write_message(json.dumps({'msg': 'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None,
                         "No response from server because authorization "
                         "not provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         connection_count, "+0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         id_count, "+0 websocket connections.")

    @gen_test
    def test_bad_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        headers = {'authorization': 'gibberish'}
        ws_client = yield self.ws_connect('/supervisor/',
                                          headers=headers)
        ws_client.write_message(json.dumps({'msg': 'update'}))
        response = yield ws_client.read_message()
        self.assertEqual(
            response, None, "No response from server because bad "
                            "authorization provided.")
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         connection_count, "+0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         id_count, "+0 websocket connections.")

    @gen_test
    def test_successful_authorization(self):
        connection_count = len(SupervisorAgentHandler.Connections.keys())
        id_count = len(SupervisorAgentHandler.IDs.keys())
        headers = {'authorization': self.AGENT_TOKEN}
        ws_client = yield self.ws_connect('/supervisor/',
                                          headers=headers)
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys(
        )), connection_count + 1, "+1 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         id_count + 1, "+1 websocket connections.")
        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         connection_count, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         id_count, "0 websocket connections.")

    @gen_test
    def test_snapshot_update(self):
        update_0 = open(os.path.join(
            resources, 'snapshots', 'valid_0.json')).read()
        update_1 = open(os.path.join(
            resources, 'snapshots', 'valid_1.json')).read()
        headers = {'authorization': self.AGENT_TOKEN}
        client = yield self.ws_connect('/supervisor/',
                                       headers=headers)
        client.write_message(update_0)
        response = yield client.read_message()
        self.assertEqual(json.loads(response),
                         json.loads(SupervisorAgent.snapshot_update_success))

        client.write_message(update_1)
        response = yield client.read_message()
        self.assertEqual(json.loads(response),
                         json.loads(SupervisorAgent.snapshot_update_success))

        client.write_message('modelsformed json')
        response = yield client.read_message()
        self.assertEqual(json.loads(response),
                         json.loads(SupervisorAgentHandler.invalid_json_error))

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         0, "0 websocket connections.")

    @gen_test
    def test_state_update(self):
        state_0 = open(os.path.join(resources, 'states',
                                    'valid_0.json')).read().split('\n')
        state_1 = open(os.path.join(resources, 'states',
                                    'valid_1.json')).read().split('\n')
        headers = {'authorization': self.AGENT_TOKEN}
        client = yield self.ws_connect('/supervisor/', headers=headers)

        for state in state_0:
            client.write_message(state)
            response = yield client.read_message()
            self.assertEqual(json.loads(response),
                             json.loads(SupervisorAgent.state_update_success))

        for state in state_1:
            client.write_message(state)
            response = yield client.read_message()
            self.assertEqual(json.loads(response),
                             json.loads(SupervisorAgent.state_update_success))

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         0, "0 websocket connections.")

    @gen_test
    def test_state_update_bad_start_pid_value(self):
        state = json.dumps({"state": {"group": "celery", "name": "celery",
                                      "statename": "STOPPING", "pid": "8593",
                                      "start": 'asdf', "state": 40}})
        headers = {'authorization': self.AGENT_TOKEN}
        client = yield self.ws_connect('/supervisor/', headers=headers)

        client.write_message(state)
        response = yield client.read_message()
        expected_error = {'status': 'error', 'errors':
                          [{'details': 'must be of integer type',
                            'arg': 'start'},
                           {'details': 'must be of integer type',
                            'arg': 'pid'}]}
        self.assertEqual(json.loads(response), expected_error)

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         0, "0 websocket connections.")

    @gen_test
    def test_state_update_missing_values(self):
        state = json.dumps({"state": {"group": "celery",
                                      "statename": "STOPPING",
                                      "pid": 8593, "start": 1460513750,
                                      "state": 40}})
        headers = {'authorization': self.AGENT_TOKEN}
        client = yield self.ws_connect('/supervisor/', headers=headers)

        client.write_message(state)
        response = yield client.read_message()
        expected_error = {'status': 'error', 'errors': [
            {'details': 'required field', 'arg': 'name'}]}
        self.assertEqual(json.loads(response), expected_error)

        client.close()
        yield self.close_future

        self.assertEqual(len(SupervisorAgentHandler.Connections.keys()),
                         0, "0 websocket connections.")
        self.assertEqual(len(SupervisorAgentHandler.IDs.keys()),
                         0, "0 websocket connections.")

    @gen_test
    def test_system_stats(self):
        stats = json.dumps({'system': {'dist_name': 'Ubuntu',
                                       'dist_version': '15.10',
                                       'hostname': 'client',
                                       'num_cores': 3,
                                       'memory': 1040834560,
                                       'processor': 'x86_64'}})
        headers = {'authorization': self.AGENT_TOKEN}
        agent = yield self.ws_connect('/supervisor/', headers=headers)

        agent.write_message(stats)
        response = yield agent.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorAgent.system_stats_update_success))

        # missing num_cores
        incomplete_stats = json.dumps({'system': {'dist_name': 'Ubuntu',
                                                  'dist_version': '15.10',
                                                  'hostname': 'client',
                                                  'memory': 1040834560,
                                                  'processor': 'x86_64'}})
        agent.write_message(incomplete_stats)
        response = yield agent.read_message()
        expected_error = {'status': 'error', 'errors': [
            {'details': 'required field', 'arg': 'num_cores'}]}
        self.assertEqual(json.loads(response), expected_error)

        agent.close()
        yield self.close_future


class SupervisorAgentMock(object):

    def __init__(self, id, ip):
        self.id = id
        self.ip = ip
        self.session = models.Session()
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
        tokens = [UserAuthToken(user=user),
                  UserAuthToken(user=User(name='User B',
                                          email='user_b@example.com',
                                          is_admin=False,
                                          password='randompasswordb')),
                  UserAuthToken(user=User(name='User C',
                                          email='user_c@example.com',
                                          is_admin=True,
                                          password='randompasswordc'))]
        models.session.add_all(tokens)
        models.session.commit()

        agent = Agent(name='Agent 0')
        models.session.add(AgentAuthToken(agent=agent))
        models.session.commit()
        druid.connection = PyDruidMock()
        druid.plyql = PlyQLMock()
        scc.initialize()

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
        ws_client.write_message(json.dumps({'cmd': 'restart'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because "
                                         "authorization not provided.")
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()),
                         connection_count, "+0 websocket connections.")

    @gen_test
    def test_bad_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        headers = {'authorization': 'gibberish'}
        ws_client = yield self.ws_connect('/client/supervisor/',
                                          headers=headers)
        ws_client.write_message(json.dumps({'cmd': 'restart'}))
        response = yield ws_client.read_message()
        self.assertEqual(response, None, "No response from server because "
                                         "bad authorization provided.")
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()),
                         connection_count, "+0 websocket connections.")

    @gen_test
    def test_successful_authorization(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        headers = {'authorization': self.USER_TOKEN}
        ws_client = yield self.ws_connect('/client/supervisor/',
                                          headers=headers)
        self.assertEqual(len(SupervisorClientHandler.Connections.keys(
        )), connection_count + 1, "+1 websocket connections.")
        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()),
                         connection_count, "0 websocket connections.")

    @gen_test
    def test_cmd_success(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        headers = {'authorization': self.USER_TOKEN}
        ws_client = yield self.ws_connect('/client/supervisor/',
                                          headers=headers)
        self.assertEqual(len(SupervisorClientHandler.Connections.keys(
        )), connection_count + 1, "+1 websocket connections.")

        headers = {'authorization': self.AGENT_TOKEN}
        ws_agent = yield self.ws_connect('/supervisor/',
                                         headers=headers)

        ws_client.write_message(json.dumps(
            {'cmd': 'sub', 'id': self.AGENT_ID, 'process': 'process_0'}))
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClient.cmd_success_message('sub')))

        response = yield ws_client.read_message()
        data = json.loads(response)['snapshot']
        self.assertEqual(data['process'], 'process_0')
        self.assertEqual(data['id'], self.AGENT_ID)
        for stat in data['stats']:
            self.assertTrue(validators.timestamp(stat['timestamp']))
            self.assertTrue(type(stat['cpu']) == float)
            self.assertTrue(type(stat['mem']) == int)

        message = {'cmd': 'restart', 'id': self.AGENT_ID,
                   'process': 'process_0'}
        yield ws_client.write_message(json.dumps(message))
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClient.cmd_success_message('restart')))

        response = yield ws_agent.read_message()
        self.assertEqual(json.loads(response), {'cmd': 'restart process_0'})

        state_0 = open(os.path.join(resources, 'states',
                                    'valid_0.json')).read().split('\n')

        for state in state_0:
            ws_agent.write_message(state)
            response = yield ws_agent.read_message()
            self.assertEqual(json.loads(response), json.loads(
                SupervisorAgent.state_update_success))

        for state in state_0:
            response = yield ws_client.read_message()
            data = json.loads(response)['state']
            sent_data = json.loads(state)['state']
            self.assertEqual(sent_data['name'], data['name'])
            self.assertEqual(sent_data['statename'], data['state'])
            self.assertEqual(datetime.utcfromtimestamp(sent_data['start']).
                             strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                             data['started'])

        # Wait for another message sent from scc to the client
        response = yield ws_client.read_message()
        data = json.loads(response)['snapshot']
        self.assertEqual(data['process'], 'process_0')
        self.assertEqual(data['id'], self.AGENT_ID)
        for stat in data['stats']:
            self.assertTrue(validators.timestamp(stat['timestamp']))
            self.assertTrue(type(stat['cpu']) == float)
            self.assertTrue(type(stat['mem']) == int)

        ws_client.write_message(json.dumps(
            {'cmd': 'unsub', 'id': self.AGENT_ID, 'process': 'process_0'}))
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClient.cmd_success_message('unsub')))

        ws_client.write_message(json.dumps(
            {'cmd': 'sub', 'id': self.AGENT_ID, 'process': 'process_1'}))
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClient.cmd_success_message('sub')))

        response = yield ws_client.read_message()
        data = json.loads(response)['snapshot']
        self.assertEqual(data['process'], 'process_1')
        self.assertEqual(data['id'], self.AGENT_ID)
        for stat in data['stats']:
            self.assertTrue(validators.timestamp(stat['timestamp']))
            self.assertTrue(type(stat['cpu']) == float)
            self.assertTrue(type(stat['mem']) == int)

        message = {'cmd': 'restart', 'id': self.AGENT_ID,
                   'process': 'process_1'}
        yield ws_client.write_message(json.dumps(message))
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClient.cmd_success_message('restart')))

        response = yield ws_agent.read_message()
        self.assertEqual(json.loads(response), {'cmd': 'restart process_1'})

        state_1 = open(os.path.join(resources, 'states',
                                    'valid_1.json')).read().split('\n')

        for state in state_1:
            ws_agent.write_message(state)
            response = yield ws_agent.read_message()
            self.assertEqual(json.loads(response), json.loads(
                SupervisorAgent.state_update_success))

        for state in state_1:
            response = yield ws_client.read_message()
            data = json.loads(response)['state']
            sent_data = json.loads(state)['state']
            self.assertEqual(sent_data['name'], data['name'])
            self.assertEqual(sent_data['statename'], data['state'])
            self.assertEqual(datetime.utcfromtimestamp(sent_data['start']).
                             strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                             data['started'])

        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()),
                         connection_count, "0 websocket connections.")

        ws_agent.close()
        yield self.close_future
        time.sleep(1.0)

    @gen_test
    def test_cmd_failure(self):
        connection_count = len(SupervisorClientHandler.Connections.keys())
        headers = {'authorization': self.USER_TOKEN}
        ws_client = yield self.ws_connect('/client/supervisor/',
                                          headers=headers)
        self.assertEqual(len(SupervisorClientHandler.Connections.keys(
        )), connection_count + 1, "+1 websocket connections.")

        ws_client.write_message(json.dumps(
            {'cmd': 'restart', 'id': 100, 'process': 'web'}))
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClient.agent_not_connected_error))

        ws_client.write_message(json.dumps(
            {'id': self.AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        expected_error = {'status': 'error', 'errors': [
            {'details': 'required field', 'arg': 'cmd'}]}
        self.assertEqual(json.loads(response), expected_error)

        ws_client.write_message(json.dumps(
            {'cmd': 'restart', 'process': 'web'}))
        response = yield ws_client.read_message()
        expected_error = {'status': 'error', 'errors': [
            {'details': 'required field', 'arg': 'id'}]}
        self.assertEqual(json.loads(response), expected_error)

        ws_client.write_message(json.dumps(
            {'cmd': 'restart', 'id': self.AGENT_ID}))
        response = yield ws_client.read_message()
        expected_error = {'status': 'error', 'errors': [
            {'details': 'required field', 'arg': 'process'}]}
        self.assertEqual(json.loads(response), expected_error)

        ws_client.write_message(json.dumps(
            {'cmd': 'unknown', 'id': self.AGENT_ID, 'process': 'web'}))
        response = yield ws_client.read_message()
        expected_error = {'status': 'error', 'errors': [
            {'details': 'unallowed value unknown', 'arg': 'cmd'}]}
        self.assertEqual(json.loads(response), expected_error)

        ws_client.write_message('invalid json')
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClientHandler.invalid_json_error))

        ws_client.write_message('')
        response = yield ws_client.read_message()
        self.assertEqual(json.loads(response), json.loads(
            SupervisorClientHandler.invalid_json_error))

        ws_client.close()
        yield self.close_future
        self.assertEqual(len(SupervisorClientHandler.Connections.keys()),
                         connection_count, "0 websocket connections.")
