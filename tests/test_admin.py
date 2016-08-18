#! /usr/bin/env python
from __future__ import absolute_import

from admin.admin import Admin
from admin.config import config
from db import dal, User, UserAuthToken, Agent, AgentAuthToken
from tempfile import NamedTemporaryFile

import mock
import unittest


class MockArgs(object):
    def __init__(self, tmp_file):
        self.log_level = 'DEBUG'
        self.log_file = tmp_file.name,
        self.database = 'sqlite:///:memory:'
        self.config = None


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_file = NamedTemporaryFile()
        config.resolveArgs(MockArgs(cls.tmp_file))
        cls.admin = Admin()

    def tearDown(self):
        try:
            dal.session.query(User).delete()
            dal.session.query(UserAuthToken).delete()
            dal.session.query(Agent).delete()
            dal.session.query(AgentAuthToken).delete()
            dal.session.commit()
        except:
            dal.session.rollback()
        dal.session.close()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_user(self, mock_raw_input, mock_getpass):  
        mock_raw_input.side_effect = ['marcw@silverfern.io', 'Marc Wilson', 'Y']
        mock_getpass.side_effect = ['asdfasdf', 'asdfasdf']
        TestApp.admin.create_user()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_user(self, mock_raw_input, mock_getpass):
        password = 'asdfasdf'
        phil = User(name='Phil Lake',
                    email='philip@gmail.com',
                    is_admin=False,
                    password=password)
        colin = User(name='Colin Ng',
                    email='colin@ngland.net',
                    is_admin=True,
                    password=password)
        dal.session.add(phil)
        dal.session.add(colin)
        dal.session.commit()
        mock_raw_input.side_effect = [colin.email, phil.email]
        mock_getpass.side_effect = [password]
        TestApp.admin.delete_user()

    def test_list_users(self):
        TestApp.admin.list_users()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_user_auth_token(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        user = User(name='Joe User',
                    email='user@gmail.com',
                    is_admin=False,
                    password='qwerqwer')
        dal.session.add(admin)
        dal.session.add(user)
        dal.session.commit()  
        mock_raw_input.side_effect = [admin.email, user.email]
        mock_getpass.side_effect = [password]
        TestApp.admin.create_user_auth_token()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_user_auth_token(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        user = User(name='Joe User',
                    email='user@gmail.com',
                    is_admin=False,
                    password='qwerqwer')
        token = UserAuthToken(user=user)
        dal.session.add(admin)
        dal.session.add(token)
        dal.session.commit()
        mock_raw_input.side_effect = [admin.email, user.email]
        mock_getpass.side_effect = [password]
        TestApp.admin.delete_user_auth_token()

    def test_list_user_auth_tokens(self):
        TestApp.admin.list_user_auth_tokens()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_agent(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        dal.session.add(admin)
        dal.session.commit()
        mock_raw_input.side_effect = [admin.email, '']
        mock_getpass.side_effect = [password]
        TestApp.admin.create_agent()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_agent(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        agent = Agent(name='Agent 007')
        dal.session.add(admin)
        dal.session.add(agent)
        dal.session.commit()
        mock_raw_input.side_effect = [admin.email, str(agent.id)]
        mock_getpass.side_effect = [password]
        TestApp.admin.delete_agent()

    def test_list_agents(self):
        TestApp.admin.list_agents()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_agent_auth_token(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        agent = Agent(name='Agent 007')
        dal.session.add(admin)
        dal.session.add(agent)
        dal.session.commit()
        mock_raw_input.side_effect = [admin.email, str(agent.id)]
        mock_getpass.side_effect = [password]
        TestApp.admin.create_agent_auth_token()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_agent_auth_token(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        agent = Agent(name='Agent 007')
        token = AgentAuthToken(agent=agent)
        dal.session.add(admin)
        dal.session.add(token)
        dal.session.commit()
        mock_raw_input.side_effect = [admin.email, str(agent.id)]
        mock_getpass.side_effect = [password]
        TestApp.admin.delete_agent_auth_token()

    def test_list_agent_auth_tokens(self):
        TestApp.admin.list_agent_auth_tokens()
