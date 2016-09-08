# Adapted from
# https://github.com/tornadoweb/tornado/blob/master/tornado/test/httpclient_test.py
import json
import os

from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application, url
from tornado import gen

from agentserver.http.client import (HTTPVersionHandler, HTTPTokenHandler,
                         HTTPDetailHandler, HTTPCommandHandler,
                         HTTPListHandler)
from agentserver.http.agent import HTTPAgentUpdateHandler, HTTPAgentDetailHandler

from mocks.timeseries import KafkaProducerMock, PyDruidMock, PlyQLMock
from ws_helpers import websocket_connect, MockSupervisorAgentHandler

from agentserver.db.models import (models, User, UserAuthToken, Agent,
                       AgentAuthToken, AgentDetail)
from agentserver.db.timeseries import kafka, druid
from agentserver.clients.supervisorclientcoordinator import scc


resources = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), 'resources')


class TestHTTP(AsyncHTTPTestCase):

    @classmethod
    def setUpClass(cls):
        models.connect('sqlite:///:memory:')
        kafka.connection = KafkaProducerMock()
        druid.connection = PyDruidMock()
        druid.plyql = PlyQLMock()

        # Generate users
        cls.EMAIL = 'user_a@example.com'
        cls.PASSWORD = 'randompassworda'
        user = User(name='User A',
                    email=cls.EMAIL,
                    is_admin=True,
                    password=cls.PASSWORD)
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

        # Generate agents
        agent_0 = Agent(name='Agent 0')
        agent_1 = Agent(name='Agent 1')
        agent_2 = Agent(name='Agent 2')
        agent_3 = Agent(name='Agent 3')

        models.session.add_all([AgentAuthToken(agent=agent_0),
                                AgentAuthToken(agent=agent_1),
                                AgentAuthToken(agent=agent_2),
                                AgentAuthToken(agent=agent_3)])

        models.session.add(AgentDetail(agent=agent_0,
                                       hostname='agent_1',
                                       processor='x86_64',
                                       num_cores=2,
                                       memory=8372064256,
                                       dist_name='Ubuntu',
                                       dist_version='15.04'))

        models.session.commit()
        scc.initialize()

        cls.TOKEN = user.token.uuid
        cls.AGENT_ID_0 = agent_0.id
        cls.AGENT_ID_1 = agent_1.id
        cls.AGENT_TOKEN_0 = agent_0.token.uuid
        cls.AGENT_TOKEN_1 = agent_1.token.uuid
        cls.AGENT_TOKEN_2 = agent_2.token.uuid
        cls.AGENT_TOKEN_3 = agent_3.token.uuid

    @classmethod
    def tearDownClass(cls):
        models.session.rollback()
        models.session.close()

    def get_app(self):
        self.close_future = Future()
        return Application([
            url(r'/', HTTPVersionHandler),
            url(r'/token/', HTTPTokenHandler),
            url(r'/list/', HTTPListHandler),
            url(r'/command/', HTTPCommandHandler),
            url(r'/detail/', HTTPDetailHandler),
            url(r'/agent/update/', HTTPAgentUpdateHandler),
            url(r'/agent/detail/', HTTPAgentDetailHandler),
            ('/supervisor/', MockSupervisorAgentHandler,
                dict(close_future=self.close_future)),
        ])

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

    def test_http_handler(self):
        response = self.fetch('/', method='GET')
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPVersionHandler.response))
        self.assertEqual(response.code, 200)

    def test_http_token_handler_success(self):
        headers = {'username': self.EMAIL, 'password': self.PASSWORD}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertTrue('token' in json.loads(response.body))
        self.assertEqual(response.code, 200)

    def test_http_token_handler_failure(self):
        headers = {'username': self.EMAIL, 'password': 'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

        headers = {'username': 'asdf', 'password': 'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

        headers = {'gibberish': 'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

        response = self.fetch('/token/', method='GET')
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

    def test_http_list_handler(self):
        headers = {'authorization': self.TOKEN}
        response = self.fetch('/list/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        for item in response_data:
            self.assertTrue('id' in item)
            self.assertTrue('processes' in item)
            self.assertTrue('state' in item)
            self.assertTrue('name' in item)
        self.assertEqual(response.code, 200)
        self.assertEqual(len(response_data), Agent.count())

        headers = {'authorization': 'bad token'}
        response = self.fetch('/list/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPCommandHandler.not_authorized_error))
        self.assertEqual(response.code, 401)

        response = self.fetch('/list/', method='GET')
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPCommandHandler.not_authorized_error))
        self.assertEqual(response.code, 401)

    def test_http_command_bad_args_handler(self):
        headers = {'authorization': self.TOKEN}
        # Unconnected agent
        body = json.dumps({'cmd': 'restart', 'id': self.AGENT_ID_1,
                           'process': 'process_0'})
        response = self.fetch('/command/',
                              method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPCommandHandler.
                                    cmd_error(self.AGENT_ID_1)))

        # Unknown command and missing argument
        body = json.dumps({'cmd': 'unknown', 'id': self.AGENT_ID_1})
        response = self.fetch('/command/',
                              method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
                          [{'details': 'required field', 'arg': 'process'},
                           {'details': 'unallowed value unknown',
                            'arg': 'cmd'}]}
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), expected_error)

        # Missing argument
        body = json.dumps({'cmd': 'restart', 'id': self.AGENT_ID_1})
        response = self.fetch('/command/',
                              method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
                          [{'details': 'required field', 'arg': 'process'}]}
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), expected_error)

        # Bad json
        response = self.fetch('/command/',
                              method='POST', headers=headers,
                              body='invalid json')
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPCommandHandler.invalid_json_error))

    @gen_test
    def test_http_command_handler(self):
        headers = {'authorization': self.AGENT_TOKEN_0}
        ws_agent = yield self.ws_connect('/supervisor/', headers=headers)

        headers = {'authorization': self.TOKEN}
        body = json.dumps({'cmd': 'restart', 'id': self.AGENT_ID_0,
                           'process': 'process_0'})
        response = yield self.http_client.fetch(self.get_url('/command/'),
                                                method='POST', headers=headers,
                                                body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPCommandHandler.cmd_success('restart')))

        response = yield ws_agent.read_message()
        self.assertEqual(json.loads(response), {'cmd': 'restart process_0'})

        ws_agent.close()
        yield self.close_future

    def test_http_detail_handler_success(self):
        headers = {'authorization': self.TOKEN}
        body = json.dumps({'id': 1})
        response = self.fetch('/detail/', method='POST',
                              headers=headers, body=body)
        detail = models.Session().query(AgentAuthToken) \
            .filter(AgentAuthToken.uuid == self.AGENT_TOKEN_0) \
            .one().agent.detail
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), detail.__json__())

    def test_http_detail_handler_failure(self):
        headers = {'authorization': self.TOKEN}
        body = json.dumps({'id': 4})
        response = self.fetch('/detail/', method='POST',
                              headers=headers, body=body)
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPDetailHandler.invalid_id_error))
        self.assertEqual(response.code, 400)

        body = 'invalid json'
        response = self.fetch('/detail/', method='POST',
                              headers=headers, body=body)
        self.assertEqual(json.loads(response.body),
                         json.loads(HTTPDetailHandler.invalid_json_error))
        self.assertEqual(response.code, 400)

    def test_http_agent_detail_update_handler(self):
        count_before = AgentDetail.count()

        data = json.loads(open(os.path.join(resources,
                                            'system_stats',
                                            'valid_2.json')).read())['system']
        headers = {'authorization': self.AGENT_TOKEN_0}
        body = json.dumps(data)

        response = self.fetch(
            '/agent/detail/', method='POST', headers=headers, body=body)
        expected_response = HTTPAgentDetailHandler.success_response_updated
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body),
                         json.loads(expected_response))

        token = models.Session().query(AgentAuthToken).filter(
            AgentAuthToken.uuid == self.AGENT_TOKEN_0).one()
        detail = token.agent.detail.__json__()
        detail.pop('updated')
        detail.pop('created')
        self.assertEqual(data, detail)
        self.assertEqual(count_before, AgentDetail.count())

    def test_http_agent_detail_create_handler(self):
        count_before = AgentDetail.count()

        data = json.loads(open(os.path.join(resources,
                                            'system_stats',
                                            'valid_2.json')).read())['system']
        headers = {'authorization': self.AGENT_TOKEN_1}
        body = json.dumps(data)

        response = self.fetch(
            '/agent/detail/', method='POST', headers=headers, body=body)
        expected_response = HTTPAgentDetailHandler.success_response_created
        self.assertEqual(response.code, 201)
        self.assertEqual(json.loads(response.body),
                         json.loads(expected_response))

        token = models.Session().query(AgentAuthToken).filter(
            AgentAuthToken.uuid == self.AGENT_TOKEN_1).one()
        detail = token.agent.detail.__json__()
        detail.pop('updated')
        detail.pop('created')
        self.assertEqual(data, detail)
        self.assertEqual(count_before + 1, AgentDetail.count())

    def test_http_agent_detail_handler_missing_params(self):
        count_before = AgentDetail.count()

        headers = {'authorization': self.AGENT_TOKEN_2}
        path = os.path.join(resources, 'system_stats', 'invalid_2.json')
        data = json.loads(open(path).read())['system']
        body = json.dumps(data)

        response = self.fetch(
            '/agent/detail/', method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
                          [{'details': 'required field', 'arg': 'num_cores'},
                           {'details': 'required field', 'arg': 'memory'}]}
        self.assertEqual(json.loads(response.body), expected_error)
        self.assertEqual(response.code, 400)

        self.assertEqual(count_before, AgentDetail.count())

    def test_http_agent_detail_handler_incorrect_params(self):
        count_before = AgentDetail.count()

        headers = {'authorization': self.AGENT_TOKEN_2}
        path = os.path.join(resources, 'system_stats', 'invalid_3.json')
        data = json.loads(open(path).read())['system']
        body = json.dumps(data)

        response = self.fetch(
            '/agent/detail/', method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
                          [{'details': 'must be of integer type',
                            'arg': 'num_cores'},
                           {'details': 'must be of integer type',
                            'arg': 'memory'}]}
        self.assertEqual(json.loads(response.body), expected_error)
        self.assertEqual(response.code, 400)

        self.assertEqual(count_before, AgentDetail.count())

    def test_http_agent_detail_handler_invalid_json(self):
        count_before = AgentDetail.count()
        headers = {'authorization': self.AGENT_TOKEN_2}
        response = self.fetch('/agent/detail/', method='POST',
                              headers=headers, body='invalid json')
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPAgentDetailHandler.invalid_json_error))
        self.assertEqual(response.code, 400)

        self.assertEqual(count_before, AgentDetail.count())

    def test_http_agent_update_handler(self):
        headers = {'authorization': self.AGENT_TOKEN_0}
        body = open(os.path.join(
            resources, 'snapshots', 'valid_0.json')).read()
        response = self.fetch(
            '/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPAgentUpdateHandler.snapshot_update_success))

        body = open(os.path.join(
            resources, 'snapshots', 'valid_1.json')).read()
        response = self.fetch(
            '/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPAgentUpdateHandler.snapshot_update_success))

    def test_http_agent_update_handler_invalid_json(self):
        headers = {'authorization': self.AGENT_TOKEN_0}
        response = self.fetch('/agent/update/', method='POST',
                              headers=headers, body='invalid json')
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPAgentUpdateHandler.invalid_json_error))

        body = open(os.path.join(
            resources, 'snapshots', 'invalid_0.json')).read()
        response = self.fetch(
            '/agent/update/', method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
                          [{'details': 'must be of integer type',
                            'arg': 'pid'},
                           {'details': {'0': {'0': 'must be of float type'}},
                            'arg': 'stats'}]}
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), expected_error)

    def test_http_agent_update_handler_bad_auth(self):
        headers = {'authorization': 'gibberish'}
        body = open(os.path.join(
            resources, 'snapshots', 'valid_0.json')).read()
        response = self.fetch(
            '/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body), json.loads(
            HTTPAgentUpdateHandler.not_authorized_error))
