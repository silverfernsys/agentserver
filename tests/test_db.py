#! /usr/bin/env python
import unittest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from db import (dal, User, UserAuthToken, Agent,
    AgentAuthToken, AgentDetail)


class TestDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')

    @classmethod
    def tearDownClass(cls):
        dal.session.rollback()
        dal.session.close()

    def test_users_and_user_tokens(self):
        # Generate users and tokens
        dal.session.add_all([UserAuthToken(user=User(name='User A',
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
        dal.session.commit()

        # Test that creating a new user with an
        # existing email address fails
        dal.session.add(User(name='User D',
                         email='user_a@example.com',
                         is_admin=False,
                         password='randompasswordd'))
        with self.assertRaises(IntegrityError) as e:
            dal.session.commit()

        dal.session.rollback()

        self.assertEqual(User.count(), 3)
        self.assertEqual(UserAuthToken.count(), 3)

        dal.session.delete(dal.session.query(User).filter(User.email == 'user_a@example.com').one())
        dal.session.commit()

        self.assertEqual(User.count(), 2)
        self.assertEqual(UserAuthToken.count(), 2)

    def test_agents_and_agent_tokens(self):
        # Generate agents and tokens
        agents_before = Agent.count()
        agent_tokens_before = AgentAuthToken.count()
        agent = Agent(name='Agent 0')

        dal.session.add_all([
            AgentAuthToken(agent=agent),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2'))])
        dal.session.commit()

        self.assertEqual(Agent.count(),
            agents_before + 3)
        self.assertEqual(AgentAuthToken.count(),
            agent_tokens_before + 3)

        dal.session.delete(dal.session.query(Agent).get(agent.id))
        dal.session.commit()

        self.assertEqual(Agent.count(),
            agents_before + 2)
        self.assertEqual(AgentAuthToken.count(),
            agent_tokens_before + 2)

    def test_agent_detail(self):
        agent = Agent(name='Agent')
        dal.session.add(agent)
        dal.session.commit()

        self.assertEqual(AgentDetail.count(), 0)
        args = {'dist_name': 'Ubuntu', 'dist_version': '15.10',
            'hostname': 'client', 'num_cores': 3,
            'memory': 1040834560, 'processor': 'x86_64'}
        created = AgentDetail.update_or_create(agent.id, **args)
        self.assertTrue(created)
        self.assertEqual(AgentDetail.count(), 1)

        args = {'dist_name': 'Debian', 'dist_version': '7.0',
            'hostname': 'client2', 'num_cores': 6,
            'memory': 8888888, 'processor': 'amd64'}
        created = AgentDetail.update_or_create(agent.id, **args)
        self.assertFalse(created)
        self.assertEqual(AgentDetail.count(), 1)
