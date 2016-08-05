#!/usr/bin/env python
# Adapted from https://github.com/tornadoweb/tornado/blob/master/tornado/test/httpclient_test.py
import json
import os
import tempfile
import time
import urllib
import mock

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, RequestHandler, url

from http import (HTTPVersionHandler, HTTPStatusHandler,
    HTTPTokenHandler, HTTPListHandler, HTTPDetailHandler,
    HTTPDetailCreateUpdateHandler, HTTPAgentUpdateHandler)

from db import dal, kal, User, UserAuthToken, Agent, AgentAuthToken, AgentDetail


class HTTPTestCase(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')
        dal.session = dal.Session()
        kal.connect('debug')

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

        dal.session.add_all([AgentAuthToken(agent=agent_0),
            AgentAuthToken(agent=agent_1),
            AgentAuthToken(agent=agent_2)])

        dal.session.add(AgentDetail(agent=agent_0,
            hostname='agent_1',
            processor='x86_64',
            num_cores=2,
            memory=8372064256,
            dist_name='Ubuntu',
            dist_version='15.04'))

        dal.session.commit()

        cls.TOKEN = user.token.uuid
        cls.AGENT_TOKEN_0 = agent_0.token.uuid
        cls.AGENT_TOKEN_1 = agent_1.token.uuid
        cls.AGENT_TOKEN_2 = agent_2.token.uuid

        cls.FIXTURES_DIR =  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

    @classmethod
    def tearDownClass(cls):
        dal.session.rollback()
        dal.session.close()

    def get_app(self):
        return Application([
            url(r'/', HTTPVersionHandler),
            url(r'/status/', HTTPStatusHandler),
            url(r'/token/', HTTPTokenHandler),
            url(r'/list/', HTTPListHandler),
            url(r'/detail/', HTTPDetailHandler),
            url(r'/detail_update/', HTTPDetailCreateUpdateHandler),
            url(r'/agent/update/', HTTPAgentUpdateHandler),
        ])

    def test_http_handler(self):
        response = self.fetch('/', method='GET')
        response_data = json.loads(response.body)
        self.assertTrue('version' in response_data)
        self.assertEqual(response.code, 200)

    def test_http_token_handler_success(self):
        headers = {'username':HTTPTestCase.EMAIL, 'password':HTTPTestCase.PASSWORD}
    	response = self.fetch('/token/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(HTTPTestCase.TOKEN, response_data['token'])

    def test_http_token_handler_failure(self):
        headers = {'username':HTTPTestCase.EMAIL, 'password':'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertEqual(response_data['error'], 'invalid username/password')

        headers = {'username':'asdf', 'password':'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertEqual(response_data['error'], 'invalid username/password')

        headers = {'gibberish':'gibberish'}
        response = self.fetch('/token/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertEqual(response_data['error'], 'invalid username/password')

    def test_http_status_handler(self):
        headers = {'authorization':HTTPTestCase.TOKEN}
        response = self.fetch('/status/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        # print('response_data: %s' % response_data)
        # self.assertEqual(len(response_data), 3)
        self.assertEqual(response.code, 200)

    def test_http_list_handler(self):
        headers = {'authorization':HTTPTestCase.TOKEN}
        response = self.fetch('/list/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        # print('response_data: %s' % response_data)
        self.assertEqual(response.code, 200)
        self.assertEqual(len(response_data), 3)

    def test_http_detail_handler_success(self):
        headers = {'authorization':HTTPTestCase.TOKEN}
        body = json.dumps({'id': 1})
        response = self.fetch('/detail/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertIn('hostname', response_data)
        self.assertIn('processor', response_data)
        self.assertIn('num_cores', response_data)
        self.assertIn('memory', response_data)
        self.assertIn('dist_name', response_data)
        self.assertIn('dist_version', response_data)
        self.assertIn('updated', response_data)
        self.assertIn('created', response_data)
        self.assertEqual(response.code, 200)

    def test_http_detail_handler_failure(self):
        headers = {'authorization':HTTPTestCase.TOKEN}
        body = json.dumps({'id': 4})
        response = self.fetch('/detail/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'invalid id')
        self.assertEqual(response.code, 400)

    def test_http_detail_update_handler(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_1_update'
        processor = 'x86_64_update'
        num_cores = 3
        memory = 9999999
        dist_name = 'Ubuntu_update'
        dist_version = '15.04_update'

        headers = {'authorization':HTTPTestCase.AGENT_TOKEN_0}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'num_cores': num_cores,
            'memory': memory,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/detail_update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertIn('status', response_data)
        self.assertEqual(response_data['status'], 'success')

        token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == HTTPTestCase.AGENT_TOKEN_0).one()
        detail = token.agent.details

        self.assertEqual(detail.hostname, hostname)
        self.assertEqual(detail.processor, processor)
        self.assertEqual(detail.num_cores, num_cores)
        self.assertEqual(detail.memory, memory)
        self.assertEqual(detail.dist_name, dist_name)
        self.assertEqual(detail.dist_version, dist_version)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_detail_update_handler_missing_params(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_1_update'
        processor = 'x86_64_update'
        dist_name = 'Ubuntu_update'
        dist_version = '15.04_update'

        headers = {'authorization':HTTPTestCase.AGENT_TOKEN_0}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/detail_update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertIn('status', response_data)
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['error_type'], 'missing value')
        self.assertIn('value', response_data)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_detail_create_handler(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_2'
        processor = 'amd64'
        num_cores = 1
        memory = 88888888
        dist_name = 'Ubuntu'
        dist_version = '14.04'

        headers = {'authorization':HTTPTestCase.AGENT_TOKEN_1}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'num_cores': num_cores,
            'memory': memory,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/detail_update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 201)
        self.assertIn('status', response_data)
        self.assertEqual(response_data['status'], 'success')

        token = dal.Session().query(AgentAuthToken).filter(AgentAuthToken.uuid == HTTPTestCase.AGENT_TOKEN_1).one()
        detail = token.agent.details

        self.assertEqual(detail.hostname, hostname)
        self.assertEqual(detail.processor, processor)
        self.assertEqual(detail.num_cores, num_cores)
        self.assertEqual(detail.memory, memory)
        self.assertEqual(detail.dist_name, dist_name)
        self.assertEqual(detail.dist_version, dist_version)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before + 1, count_after)

    def test_http_detail_create_handler_missing_params(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_2'
        processor = 'amd64'
        dist_name = 'Ubuntu'
        dist_version = '14.04'

        headers = {'authorization':HTTPTestCase.AGENT_TOKEN_2}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/detail_update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertIn('status', response_data)
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['error_type'], 'missing value')
        self.assertIn('value', response_data)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_detail_create_handler_incorrect_params(self):
        count_before = dal.Session().query(AgentDetail).count()

        hostname = 'agent_2'
        processor = 'amd64'
        num_cores = 'asdf'
        memory = 'asdf'
        dist_name = 'Ubuntu'
        dist_version = '14.04'

        headers = {'authorization':HTTPTestCase.AGENT_TOKEN_2}
        body = json.dumps({
            'hostname': hostname,
            'processor': processor,
            'num_cores': num_cores,
            'memory': memory,
            'dist_name': dist_name,
            'dist_version': dist_version
        })
        response = self.fetch('/detail_update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 400)
        self.assertIn('status', response_data)
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['error_type'], 'value error')
        self.assertIn('value', response_data)

        count_after = dal.Session().query(AgentDetail).count()
        self.assertEqual(count_before, count_after)

    def test_http_agent_update_handler(self):
        headers = {'authorization': HTTPTestCase.AGENT_TOKEN_0}
        body = open(os.path.join(HTTPTestCase.FIXTURES_DIR, 'snapshot0.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(response_data['status'], 'success')

        body = open(os.path.join(HTTPTestCase.FIXTURES_DIR, 'snapshot1.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(response_data['status'], 'success')

    def test_http_agent_update_handler_bad_auth(self):
        headers = {'authorization': 'gibberish'}
        body = open(os.path.join(HTTPTestCase.FIXTURES_DIR, 'snapshot0.json')).read()
        response = self.fetch('/agent/update/', method='POST', headers=headers, body=body)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 401)
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['error_type'], 'not authorized')

