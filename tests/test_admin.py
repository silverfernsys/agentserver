#! /usr/bin/env python
from __future__ import absolute_import

from admin.admin import Admin
from admin.config import config
from db.models import mal, User, UserAuthToken, Agent, AgentAuthToken
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
            mal.session.query(User).delete()
            mal.session.query(UserAuthToken).delete()
            mal.session.query(Agent).delete()
            mal.session.query(AgentAuthToken).delete()
            mal.session.commit()
        except:
            mal.session.rollback()
        mal.session.close()

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
        mal.session.add(phil)
        mal.session.add(colin)
        mal.session.commit()
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
        mal.session.add(admin)
        mal.session.add(user)
        mal.session.commit()  
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
        mal.session.add(admin)
        mal.session.add(token)
        mal.session.commit()
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
        mal.session.add(admin)
        mal.session.commit()
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
        mal.session.add(admin)
        mal.session.add(agent)
        mal.session.commit()
        mock_raw_input.side_effect = [admin.email, agent.name]
        mock_getpass.side_effect = [password]
        TestApp.admin.delete_agent()

    def test_list_agents(self):
        TestApp.admin.list_agents()

    # @mock.patch('utils.haiku.random.choice')
    # @mock.patch('db.models.Agent.count')
    # def test_generate_agent_name(self, mock_count, mock_choice):
    #     from utils.haiku import adjs, nouns
    #     mock_count.side_effect = [5, 9000]
    #     mock_choice.side_effect = [adjs[4], nouns[10], adjs[17], nouns[21]]
    #     [adjective, noun, num] = TestApp.admin.generate_agent_name().split('-')
    #     self.assertEqual(adjective, 'silent')
    #     self.assertEqual(noun, 'sunset')
    #     self.assertEqual(len(num), 4, 'Length of number string is 4')
    #     self.assertEqual(int(num), 2137, 'Integer value is 2137')
    #     [adjective, noun, num] = TestApp.admin.generate_agent_name().split('-')
    #     self.assertEqual(adjective, 'twilight')
    #     self.assertEqual(noun, 'glade')
    #     self.assertEqual(len(num), 4, 'Length of number string is 4')
    #     self.assertEqual(int(num), 9384, 'Integer value is 9384')

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_agent_auth_token(self, mock_raw_input, mock_getpass):
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        agent = Agent(name='Agent 007')
        mal.session.add(admin)
        mal.session.add(agent)
        mal.session.commit()
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
        mal.session.add(admin)
        mal.session.add(token)
        mal.session.commit()
        mock_raw_input.side_effect = [admin.email, str(agent.id)]
        mock_getpass.side_effect = [password]
        TestApp.admin.delete_agent_auth_token()

    def test_list_agent_auth_tokens(self):
        TestApp.admin.list_agent_auth_tokens()
