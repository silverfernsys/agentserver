#! /usr/bin/env python
import unittest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from db import dal, User, UserAuthToken, Agent, AgentAuthToken


class TestDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')
        dal.session = dal.Session()

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

        self.assertEqual(dal.session.query(User).count(), 3)
        self.assertEqual(dal.session.query(UserAuthToken).count(), 3)

        dal.session.delete(dal.session.query(User).filter(User.email == 'user_a@example.com').one())
        dal.session.commit()

        self.assertEqual(dal.session.query(User).count(), 2)
        self.assertEqual(dal.session.query(UserAuthToken).count(), 2)

    def test_agents_and_agent_tokens(self):
        # Generate agents and tokens
        agent = Agent(name='Agent 0')

        dal.session.add_all([
            AgentAuthToken(agent=agent),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2'))])
        dal.session.commit()

        self.assertEqual(dal.session.query(Agent).count(), 3)
        self.assertEqual(dal.session.query(AgentAuthToken).count(), 3)

        dal.session.delete(dal.session.query(Agent).get(agent.id))
        dal.session.commit()

        self.assertEqual(dal.session.query(Agent).count(), 2)
        self.assertEqual(dal.session.query(AgentAuthToken).count(), 2)
