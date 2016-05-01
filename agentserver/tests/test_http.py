#!/usr/bin/env python
# Adapted from https://github.com/tornadoweb/tornado/blob/master/tornado/test/httpclient_test.py
import json
import os
import tempfile
import time

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, RequestHandler, url

from agentserver.http import HTTPVersionHandler, HTTPStatusHandler, HTTPTokenHandler
from agentserver.db import dal, User, UserAuthToken, Agent

class HTTPTestCase(AsyncHTTPTestCase):
    NAME = 'Marc Wilson'
    EMAIL = 'marcw@silverfern.io'
    PW = 'asdf'
    TOKEN = None

    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')
        dal.session = dal.Session()

        # Generate users
        user_0 = User(name=HTTPTestCase.NAME,
                         email=HTTPTestCase.EMAIL,
                         is_admin=True,
                         password=HTTPTestCase.PW)
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

        HTTPTestCase.TOKEN = token_0.uuid

        # Generate agents
        agent_0 = Agent(name='Agent 1')
        agent_1 = Agent(name='Agent 2')
        agent_2 = Agent(name='Agent 3')
        dal.session.bulk_save_objects([agent_0, agent_1, agent_2])
        dal.session.commit()

        dal.session.close()

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        super(HTTPTestCase, self).setUp()
        dal.session = dal.Session()

    def tearDown(self):
        dal.session.rollback()
        dal.session.close()

    def get_app(self):
        return Application([
            url(r'/', HTTPVersionHandler),
            url(r'/status/', HTTPStatusHandler),
            url(r'/token/', HTTPTokenHandler),
        ])

    def test_http_handler(self):
        response = self.fetch('/', method='GET')
        response_data = json.loads(response.body)
        self.assertTrue('version' in response_data)
        self.assertEqual(response.code, 200)

    def test_http_token_handler(self):
        headers = {'username':HTTPTestCase.EMAIL, 'password':HTTPTestCase.PW}
    	response = self.fetch('/token/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        self.assertEqual(response.code, 200)
        self.assertEqual(HTTPTestCase.TOKEN, response_data['token'])

    def test_http_status_handler(self):
        headers = {'authorization':HTTPTestCase.TOKEN}
        response = self.fetch('/status/', method='GET', headers=headers)
        response_data = json.loads(response.body)
        print('response_data: %s' % response_data)
        # self.assertEqual(len(response_data), 3)
        self.assertEqual(response.code, 200)
