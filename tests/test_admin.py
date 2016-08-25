from admin.admin import Admin
from admin.config import config
from db.models import mal, User, UserAuthToken, Agent, AgentAuthToken

import mock, unittest, sys
from cStringIO import StringIO
from contextlib import contextmanager
from datetime import datetime
from tempfile import NamedTemporaryFile

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
        out, sys.stdout = sys.stdout, StringIO()
        try:
            cls.admin = Admin()
            sys.stdout.seek(0)
            cls.init_output = sys.stdout.read().strip()
        finally:
            sys.stdout = out

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

    def test_init_output(self):
        self.assertEqual(self.init_output, 'Connecting to database...')

    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_user(self, mock_raw_input, mock_getpass):  
        mock_raw_input.side_effect = ['marcw@silverfern.io', 'Marc Wilson', 'Y']
        mock_getpass.side_effect = ['asdfasdf', 'asdfasdf']
        with capture(self.admin.create_user) as output:
            self.assertEqual(output, 'Successfully created user marcw@silverfern.io.')

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
        expected_output = 'Delete user: please authenticate...\n' \
            'Successfully deleted philip@gmail.com.'
        with capture(self.admin.delete_user) as output:
            self.assertEqual(output, expected_output)

    @mock.patch('db.models.datetime')
    def test_list_users(self, mock_datetime):
        # print('\n\n')
        now = datetime(2016, 1, 1)
        mock_datetime.now.return_value = now
        mal.session.add_all([User(name='User A',
             email='user_a@example.com',
             is_admin=True,
             password='randompassworda'),
        User(name='User B',
             email='user_b@example.com',
             is_admin=False,
             password='randompasswordb')])
        mal.session.commit()
        self.admin.list_users()
        # with capture(self.admin.list_users) as output:
        #     self.assertEqual(output, expected_output)

    # @mock.patch('utils.uuid.uuid')
    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_user_auth_token(self, mock_raw_input, mock_getpass):
        # mock_uuid.return_value = 'asdfasdfasdf'
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
        self.admin.create_user_auth_token()
        # with capture(self.admin.create_user_auth_token) as output:
        #     print(output)
        

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
        expected_output = 'Delete token: please authenticate...\n' \
            'Successfully deleted token for user@gmail.com.'
        with capture(self.admin.delete_user_auth_token) as output:
            self.assertEqual(output, expected_output)

    def test_list_user_auth_tokens(self):
        mal.session.add_all([
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
        mal.session.commit()
        self.admin.list_user_auth_tokens()

    @mock.patch('utils.haiku.random.choice')
    @mock.patch('getpass.getpass')
    @mock.patch('__builtin__.raw_input')
    def test_create_agent(self, mock_raw_input, mock_getpass, mock_choice):
        mock_choice.side_effect = ['dark', 'flower']
        password='asdfasdf'
        admin = User(name='Joe Admin',
                    email='admin@gmail.com',
                    is_admin=True,
                    password=password)
        mal.session.add(admin)
        mal.session.commit()
        mock_raw_input.side_effect = [admin.email, '']
        mock_getpass.side_effect = [password]
        expected_output = 'Create agent: please authenticate...\n' \
            'Successfully created agent dark-flower-7469'
        with capture(self.admin.create_agent) as output:
            self.assertEqual(output, expected_output)

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
        expected_output = 'Delete agent: please authenticate...\n' \
            'Successfully deleted agent Agent 007'
        with capture(self.admin.delete_agent) as output:
            self.assertEqual(output, expected_output)


    def test_list_agents(self):
        mal.session.add_all([
            Agent(name='Agent 0'),
            Agent(name='Agent 1'),
            Agent(name='Agent 2'),
            Agent(name='Agent 3')])
        mal.session.commit()
        self.admin.list_agents()

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
        self.admin.create_agent_auth_token()

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
        expected_output = 'Delete agent token: please authenticate...\n' \
            'Successfully deleted token for 1. Agent 007'
        with capture(self.admin.delete_agent_auth_token) as output:
            self.assertEqual(output, expected_output)

    def test_list_agent_auth_tokens(self):
        mal.session.add_all([
            AgentAuthToken(agent=Agent(name='Agent 0')),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2')),
            AgentAuthToken(agent=Agent(name='Agent 3'))])
        mal.session.commit()
        self.admin.list_agent_auth_tokens()
