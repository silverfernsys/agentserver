from admin import Admin
from db.models import models, User, UserAuthToken, Agent, AgentAuthToken

import mock
import unittest
import sys
import os
from cStringIO import StringIO
from contextlib import contextmanager
from datetime import datetime
from tempfile import NamedTemporaryFile


resources = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), 'resources')


# http://schinckel.net/2013/04/15/capture-and-test-sys.stdout-sys.stderr-in-unittest.testcase/
@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read().strip()
    finally:
        sys.stdout = out


class MockConfig(object):

    def __init__(self):
        self.log_level = 'DEBUG'
        self.log_file = NamedTemporaryFile().name
        self.database = 'sqlite:///:memory:'
        self.config = None

    def parse(self):
        pass


class TestApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        out, sys.stdout = sys.stdout, StringIO()
        try:
            cls.admin = Admin(MockConfig())
            sys.stdout.seek(0)
            cls.init_output = sys.stdout.read().strip()
        finally:
            sys.stdout = out

    def tearDown(self):
        try:
            models.session.query(User).delete()
            models.session.query(UserAuthToken).delete()
            models.session.query(Agent).delete()
            models.session.query(AgentAuthToken).delete()
            models.session.commit()
        except:
            models.session.rollback()
        models.session.close()

    def test_init_output(self):
        self.assertEqual(self.init_output, self.read_file('init.txt'))

    def read_file(self, filename):
        return open(os.path.join(resources,
                                 'test_admin', filename)).read().strip()

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_user(self, mock_raw_input, mock_getpass):
        mock_raw_input.side_effect = [
            'marcw@silverfern.io', 'Marc Wilson', 'Y']
        mock_getpass.side_effect = ['asdfasdf', 'asdfasdf']
        with capture(self.admin.create_user) as output:
            self.assertEqual(output, self.read_file('create_user.txt'))

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_user(self, mock_raw_input, mock_getpass):
        password = 'asdfasdf'
        phil = User(name='Phil Lake',
                    email='philip@gmail.com',
                    is_admin=False,
                    password=password).save()
        colin = User(name='Colin Ng',
                     email='colin@ngland.net',
                     is_admin=True,
                     password=password).save()
        mock_raw_input.side_effect = [colin.email, phil.email]
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('delete_user.txt')
        with capture(self.admin.delete_user) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.User.created_on', new_callable=mock.PropertyMock)
    def test_list_users(self, mock_created_on):
        mock_created_on.side_effect = [
            datetime(2016, 1, 1), datetime(2016, 2, 1)]
        User.save_all([User(name='User A',
                            email='user_a@example.com',
                            is_admin=True,
                            password='randompassworda'),
                       User(name='User B',
                            email='user_b@example.com',
                            is_admin=False,
                            password='randompasswordb')])
        expected_output = self.read_file('list_users.txt')
        with capture(self.admin.list_users) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.UserAuthToken.uuid', new_callable=mock.PropertyMock)
    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_user_auth_token(self, mock_raw_input,
                                    mock_getpass, mock_uuid):
        mock_uuid.return_value = '346bfe75a106553f715726f6c6de2b89552a3b05'
        password = 'asdfasdf'
        admin = User(name='Joe Admin',
                     email='admin@gmail.com',
                     is_admin=True,
                     password=password).save()
        user = User(name='Joe User',
                    email='user@gmail.com',
                    is_admin=False,
                    password='qwerqwer').save()
        mock_raw_input.side_effect = [admin.email, user.email]
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('create_user_auth_token.txt')
        with capture(self.admin.create_user_auth_token) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_user_auth_token(self, mock_raw_input, mock_getpass):
        password = 'asdfasdf'
        admin = User(name='Joe Admin',
                     email='admin@gmail.com',
                     is_admin=True,
                     password=password).save()
        user = User(name='Joe User',
                    email='user@gmail.com',
                    is_admin=False,
                    password='qwerqwer').save()
        UserAuthToken(user=user).save()
        mock_raw_input.side_effect = [admin.email, user.email]
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('delete_user_auth_token.txt')
        with capture(self.admin.delete_user_auth_token) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.UserAuthToken.created_on',
                new_callable=mock.PropertyMock)
    @mock.patch('db.models.UserAuthToken.uuid', new_callable=mock.PropertyMock)
    def test_list_user_auth_tokens(self, mock_uuid, mock_created_on):
        mock_uuid.side_effect = ['ee5378e881f7b24868ff9fd436d51ccc22bf8f12',
                                 'fb7ae8230108557d3328d9f0c6d32a992620460f',
                                 '87dcd304d0587baebf8d9f6dfc9e0aac0442c326']
        mock_created_on.side_effect = [datetime(2016, 1, 1),
                                       datetime(2016, 2, 1),
                                       datetime(2016, 3, 1)]
        UserAuthToken.save_all([
            UserAuthToken(user=User(name='User A',
                                    email='user_a@example.com',
                                    is_admin=True,
                                    password='randompassworda')),
            UserAuthToken(user=User(name='User B',
                                    email='user_b@example.com',
                                    is_admin=False,
                                    password='randompasswordb')),
            UserAuthToken(user=User(name='User C',
                                    email='user_c@example.com',
                                    is_admin=True,
                                    password='randompasswordc'))])
        expected_output = self.read_file('list_user_auth_tokens.txt')
        with capture(self.admin.list_user_auth_tokens) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('utils.haiku.random.choice')
    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_agent(self, mock_raw_input, mock_getpass, mock_choice):
        mock_choice.side_effect = ['dark', 'flower']
        password = 'asdfasdf'
        admin = User(name='Joe Admin',
                     email='admin@gmail.com',
                     is_admin=True,
                     password=password).save()
        mock_raw_input.side_effect = [admin.email, '']
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('create_agent.txt')
        with capture(self.admin.create_agent) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_agent(self, mock_raw_input, mock_getpass):
        password = 'asdfasdf'
        admin = User(name='Joe Admin',
                     email='admin@gmail.com',
                     is_admin=True,
                     password=password).save()
        agent = Agent(name='Agent 007').save()
        mock_raw_input.side_effect = [admin.email, agent.name]
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('delete_agent.txt')
        with capture(self.admin.delete_agent) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.Agent.created_on', new_callable=mock.PropertyMock)
    def test_list_agents(self, mock_created_on):
        mock_created_on.side_effect = [datetime(2016, 1, 1),
                                       datetime(2016, 2, 1),
                                       datetime(2016, 3, 1),
                                       datetime(2016, 4, 1)]
        Agent.save_all([
            Agent(name='Agent 0'),
            Agent(name='Agent 1'),
            Agent(name='Agent 2'),
            Agent(name='Agent 3')])
        expected_output = self.read_file('list_agents.txt')
        with capture(self.admin.list_agents) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.AgentAuthToken.uuid',
                new_callable=mock.PropertyMock)
    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_agent_auth_token(self, mock_raw_input,
                                     mock_getpass, mock_uuid):
        mock_uuid.return_value = 'afb52acc8a01a6aee832488234c252d423db1fc4'
        password = 'asdfasdf'
        admin = User(name='Joe Admin',
                     email='admin@gmail.com',
                     is_admin=True,
                     password=password).save()
        agent = Agent(name='Agent 007').save()
        mock_raw_input.side_effect = [admin.email, str(agent.id)]
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('create_agent_auth_token.txt')
        with capture(self.admin.create_agent_auth_token) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_delete_agent_auth_token(self, mock_raw_input, mock_getpass):
        password = 'asdfasdf'
        admin = User(name='Joe Admin',
                     email='admin@gmail.com',
                     is_admin=True,
                     password=password).save()
        agent = Agent(name='Agent 007').save()
        AgentAuthToken(agent=agent).save()
        mock_raw_input.side_effect = [admin.email, str(agent.id)]
        mock_getpass.side_effect = [password]
        expected_output = self.read_file('delete_agent_auth_token.txt')
        with capture(self.admin.delete_agent_auth_token) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.AgentAuthToken.created_on',
                new_callable=mock.PropertyMock)
    @mock.patch('db.models.AgentAuthToken.uuid',
                new_callable=mock.PropertyMock)
    def test_list_agent_auth_tokens(self, mock_uuid, mock_created_on):
        mock_uuid.side_effect = ['ae8d68dabc68268c0f895ff1b9fc46f3e94d3097',
                                 '3913a8ef57139a71a7aebdb24d0c4dc25e8acb41',
                                 '8507ab2c7fe1ab3789b996f16b1a960ccaf29755',
                                 '25babaa14973ae688edbaa27893a005ee662dfb0']
        mock_created_on.side_effect = [datetime(2016, 1, 1),
                                       datetime(2016, 2, 1),
                                       datetime(2016, 3, 1),
                                       datetime(2016, 4, 1)]
        AgentAuthToken.save_all([
            AgentAuthToken(agent=Agent(name='Agent 0')),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2')),
            AgentAuthToken(agent=Agent(name='Agent 3'))])
        expected_output = self.read_file('list_agent_auth_tokens.txt')
        with capture(self.admin.list_agent_auth_tokens) as output:
            self.assertEqual(output, expected_output)
