# Adapted from https://github.com/tornadoweb/tornado/blob/master/tornado/test/httpclient_test.py
import json, mock, os, re, tempfile, time

from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application, RequestHandler, url
from tornado import gen

from http import (HTTPVersionHandler, HTTPTokenHandler,
    HTTPDetailHandler, HTTPCommandHandler, HTTPListHandler,
    HTTPAgentUpdateHandler, HTTPAgentDetailHandler)

from mocks import pal_mock_query, FIXTURES_DIR
from ws_helpers import websocket_connect
from test_ws import MockSupervisorAgentHandler

from db import dal, kal, dral, pal, User, UserAuthToken, Agent, AgentAuthToken, AgentDetail
from clients.supervisorclientcoordinator import scc


class TestHTTP(AsyncHTTPTestCase):
    @classmethod
    @mock.patch('db.pal.query', side_effect=pal_mock_query)
    def setUpClass(cls, mock_query):
        dal.connect('sqlite:///:memory:')
        kal.connect('debug')
        dral.connect('debug')
        pal.connect('debug')
        dral.connection.fixtures_dir = FIXTURES_DIR

        # Generate users
        cls.EMAIL = 'user_a@example.com'
        cls.PASSWORD = 'randompassworda'
        user = User(name='User A',
                     email=cls.EMAIL,
                     is_admin=True,
                     password=cls.PASSWORD)
        dal.session.add_all([UserAuthToken(user=user),
                        UserAuthToken(user=User(name='User B',
                         email='user_b@example.com',
                         is_admin=False,
                         password='randompasswordb')),
                        UserAuthToken(user=User(name='User C',
                         email='user_c@example.com',
                         is_admin=True,
                         password='randompasswordc'))])

        # Generate agents
        agent_0 = Agent(name='Agent 0')
        agent_1 = Agent(name='Agent 1')
        agent_2 = Agent(name='Agent 2')
        agent_3 = Agent(name='Agent 3')

        dal.session.add_all([AgentAuthToken(agent=agent_0),
            AgentAuthToken(agent=agent_1),
            AgentAuthToken(agent=agent_2),
            AgentAuthToken(agent=agent_3)])

        dal.session.add(AgentDetail(agent=agent_0,
            hostname='agent_1',
            processor='x86_64',
            num_cores=2,
            memory=8372064256,
            dist_name='Ubuntu',
            dist_version='15.04'))

        dal.session.commit()
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
        dal.session.rollback()
        dal.session.close()

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

    def test_http_handler(self):
        response = self.fetch('/', method='GET')
        self.assertEqual(json.loads(response.body), json.loads(HTTPVersionHandler.response))
        self.assertEqual(response.code, 200)

    def test_http_token_handler_success(self):
        headers = {'username':self.EMAIL, 'password':self.PASSWORD}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertTrue('token' in json.loads(response.body))
        self.assertEqual(response.code, 200)

    def test_http_token_handler_failure(self):
        headers = {'username':self.EMAIL, 'password':'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body), json.loads(HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

        headers = {'username':'asdf', 'password':'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body), json.loads(HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

        headers = {'gibberish':'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        self.assertEqual(json.loads(response.body), json.loads(HTTPTokenHandler.authentication_error))
        self.assertEqual(response.code, 400)

    def test_http_list_handler(self):
        headers = {'authorization':self.TOKEN}
        response = self.fetch('/list/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        for item in response_data:
            self.assertTrue('id' in item)
            self.assertTrue('processes' in item)
            self.assertTrue('state' in item)
            self.assertTrue('name' in item)
        self.assertEqual(response.code, 200)
        self.assertEqual(len(response_data), dal.session.query(Agent).count())

    def test_http_command_bad_args_handler(self):
        headers = {'authorization':self.TOKEN}
        # Unconnected agent
        body = json.dumps({'cmd': 'restart', 'id': self.AGENT_ID_1,
            'process': 'process_0'})
        response = self.fetch('/command/',
            method='POST', headers=headers, body=body)
        data = json.loads(response.body)
        expected_data = {'status': 'error', 'errors':
            [{'arg': self.AGENT_ID_1, 'details': 'agent not connected'}]}
        self.assertEqual(response.code, 400)
        self.assertEqual(data, expected_data)

        # Unknown command and missing argument
        body = json.dumps({'cmd': 'unknown', 'id': self.AGENT_ID_1})
        response = self.fetch('/command/',
            method='POST', headers=headers, body=body)
        data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertEqual(data['status'], 'error')
        errors = [{'details': 'unallowed value unknown', 'arg': 'cmd'},
            {'details': 'required field', 'arg': 'process'}]
        self.assertEqual(sorted(data['errors'], key=lambda x: x['arg']),
            sorted(errors, key=lambda x: x['arg']))

        # Missing argument
        body = json.dumps({'cmd': 'restart', 'id': self.AGENT_ID_1})
        response = self.fetch('/command/',
            method='POST', headers=headers, body=body)
        data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertEqual(data['status'], 'error')
        errors = [{'details': 'required field', 'arg': 'process'}]
        self.assertEqual(data['errors'], errors)

        # Bad json
        body = 'junk'
        response = self.fetch('/command/',
            method='POST', headers=headers, body=body)
        data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['errors'], [{'details': 'invalid json'}])
      
    @gen_test
    def test_http_command_handler(self):
        ws_agent = yield self.ws_connect('/supervisor/',
            headers={'authorization': self.AGENT_TOKEN_0})

        headers = {'authorization':self.TOKEN}
        body = json.dumps({'cmd': 'restart', 'id': self.AGENT_ID_0,
            'process': 'process_0'})
        response = yield self.http_client.fetch(self.get_url('/command/'),
            method='POST', headers=headers, body=body)
        data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['details'], 'command restart accepted')

        response = yield ws_agent.read_message()
        response_data = json.loads(response)
        self.assertEqual(response_data['cmd'], 'restart process_0')

        ws_agent.close()
        yield self.close_future

    def test_http_detail_handler_success(self):
        headers = {'authorization':self.TOKEN}
        body = json.dumps({'id': 1})
        response = self.fetch('/detail/', method='POST', headers=headers, body=body)
        detail = dal.Session().query(AgentAuthToken) \
            .filter(AgentAuthToken.uuid == self.AGENT_TOKEN_0) \
            .one().agent.details
        data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['hostname'], detail.hostname)
        self.assertEqual(data['processor'], detail.processor)
        self.assertEqual(data['num_cores'], detail.num_cores)
        self.assertEqual(data['memory'], detail.memory)
        self.assertEqual(data['dist_name'], detail.dist_name)
        self.assertEqual(data['dist_version'], detail.dist_version)
        self.assertEqual(data['updated'], detail.updated_on.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual(data['created'], detail.created_on.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    def test_http_detail_handler_failure(self):
        headers = {'authorization':self.TOKEN}
        body = json.dumps({'id': 4})
        response = self.fetch('/detail/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'invalid id')
        self.assertEqual(response.code, 400)

    def test_http_agent_detail_handler(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_1_update'
        processor = 'x86_64_update'
        num_cores = 3
        memory = 9999999
        dist_name = 'Ubuntu_update'
        dist_version = '15.04_update'

        headers = {'authorization':self.AGENT_TOKEN_0}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'num_cores': num_cores,
            'memory': memory,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/agent/detail/', method='POST', headers=headers, body=body)
        data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['status'], 'success')

        token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == self.AGENT_TOKEN_0).one()
        detail = token.agent.details

        self.assertEqual(hostname, detail.hostname)
        self.assertEqual(processor, detail.processor)
        self.assertEqual(num_cores, detail.num_cores)
        self.assertEqual(memory, detail.memory)
        self.assertEqual(dist_name, detail.dist_name)
        self.assertEqual(dist_version, detail.dist_version)
        # self.assertEqual(data['updated'], detail.updated_on.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        # self.assertEqual(data['created'], detail.created_on.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_agent_detail_handler(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_2'
        processor = 'amd64'
        num_cores = 1
        memory = 88888888
        dist_name = 'Ubuntu'
        dist_version = '14.04'

        headers = {'authorization':self.AGENT_TOKEN_1}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'num_cores': num_cores,
            'memory': memory,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/agent/detail/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 201)
        self.assertIn('status', response_data)
        self.assertEqual(response_data['status'], 'success')

        token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == self.AGENT_TOKEN_1).one()
        detail = token.agent.details

        self.assertEqual(detail.hostname, hostname)
        self.assertEqual(detail.processor, processor)
        self.assertEqual(detail.num_cores, num_cores)
        self.assertEqual(detail.memory, memory)
        self.assertEqual(detail.dist_name, dist_name)
        self.assertEqual(detail.dist_version, dist_version)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before + 1, count_after)

    def test_http_agent_detail_handler_missing_params(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_2'
        processor = 'amd64'
        dist_name = 'Ubuntu'
        dist_version = '14.04'

        headers = {'authorization':self.AGENT_TOKEN_2}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/agent/detail/', method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
            [{'details': 'required field', 'arg': 'num_cores'},
            {'details': 'required field', 'arg': 'memory'}]}
        self.assertEqual(json.loads(response.body), expected_error)
        self.assertEqual(response.code, 400)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_agent_detail_handler_incorrect_params(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_2'
        processor = 'amd64'
        num_cores = 'asdf'
        memory = 'asdf'
        dist_name = 'Ubuntu'
        dist_version = '14.04'

        headers = {'authorization':self.AGENT_TOKEN_2}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'num_cores': num_cores,
            'memory': memory,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/agent/detail/', method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
            [{'details': 'must be of integer type', 'arg': 'num_cores'},
            {'details': 'must be of integer type', 'arg': 'memory'}]}
        self.assertEqual(json.loads(response.body), expected_error)
        self.assertEqual(response.code, 400)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_agent_detail_handler_invalid_json(self):
        count_before = dal.Session().query(AgentDetail).count()
        headers = {'authorization':self.AGENT_TOKEN_2}
        response = self.fetch('/agent/detail/', method='POST', headers=headers, body='gibberish')
        self.assertEqual(json.loads(response.body), json.loads(HTTPAgentDetailHandler.invalid_json_error))
        self.assertEqual(response.code, 400)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_agent_update_handler(self):
        headers = {'authorization': self.AGENT_TOKEN_0}
        body = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_0.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), json.loads(HTTPAgentUpdateHandler.snapshot_update_success))

        body = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_1.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), json.loads(HTTPAgentUpdateHandler.snapshot_update_success))

    def test_http_agent_update_handler_invalid_json(self):
        headers = {'authorization': self.AGENT_TOKEN_0}
        body = 'invalid json'
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), json.loads(HTTPAgentUpdateHandler.invalid_json_error))

        body = open(os.path.join(FIXTURES_DIR, 'snapshots', 'invalid_0.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        expected_error = {'status': 'error', 'errors':
            [{'details': 'must be of integer type', 'arg': 'pid'},
            {'details': {'0': {'0': 'must be of float type'}}, 'arg': 'stats'}]}
        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), expected_error)

    def test_http_agent_update_handler_bad_auth(self):
        headers = {'authorization': 'gibberish'}
        body = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_0.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body), json.loads(HTTPAgentUpdateHandler.not_authorized_error))
