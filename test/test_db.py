#! /usr/bin/env python
import unittest
from sqlalchemy.exc import IntegrityError
from agentserver.db.models import (models, User, UserAuthToken,
                       Agent, AgentAuthToken, AgentDetail)


class TestDb(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        models.connect('sqlite:///:memory:')

    @classmethod
    def tearDownClass(cls):
        models.session.rollback()
        models.session.close()

    def test_users_and_user_tokens(self):
        # Generate users and tokens
        user = User(name='User A',
                    email='user_a@example.com',
                    is_admin=True,
                    password='randompassworda')
        tokens = [UserAuthToken(user=user),
                  UserAuthToken(user=User(name='User B',
                                          email='user_b@example.com',
                                          is_admin=False,
                                          password='randompasswordb')),
                  UserAuthToken(user=User(name='User C',
                                          email='user_c@example.com',
                                          is_admin=True,
                                          password='randompasswordc'))]
        UserAuthToken.save_all(tokens)

        with self.assertRaises(IntegrityError):
            User(name='User D', email='user_a@example.com',
                 is_admin=False, password='randompasswordd').save()

        models.session.rollback()

        # Test authorize method
        self.assertEqual(User.authorize(user.token.uuid), user)
        self.assertEqual(User.authorize('non-existent token'), None)

        self.assertEqual(User.count(), 3)
        self.assertEqual(UserAuthToken.count(), 3)

        self.assertEqual(User.get(id=user.id), user)
        self.assertEqual(User.get(email=user.email), user)
        self.assertEqual(User.get(id=user.id), User.get(email=user.email))
        self.assertEqual(User.get(id=user.id, email=user.email), user)
        self.assertEqual(User.get(id=1000), None)
        self.assertEqual(User.get(), None)

        # Test delete method
        self.assertTrue(User.get(email=user.email).delete())
        self.assertRaises(AttributeError, lambda: User.get(
            'non-existent@example.com').delete())

        self.assertEqual(User.count(), 2)
        self.assertEqual(UserAuthToken.count(), 2)

    def test_agents_and_agent_tokens(self):
        # Generate agents and tokens
        agents_before = Agent.count()
        agent_tokens_before = AgentAuthToken.count()
        agent_details_before = AgentDetail.count()

        agent = Agent(name='Agent 0')

        AgentAuthToken.save_all([
            AgentAuthToken(agent=agent),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2'))])

        AgentDetail(agent=agent, dist_name='Debian', dist_version='7.0',
                    hostname='host', num_cores=8, memory=160000,
                    processor='x86_64').save()

        self.assertEqual(Agent.count(),
                         agents_before + 3)
        self.assertEqual(AgentAuthToken.count(),
                         agent_tokens_before + 3)
        self.assertEqual(AgentDetail.count(),
                         agent_details_before + 1)

        # Test authorize method
        self.assertEqual(Agent.authorize(agent.token.uuid), agent)
        self.assertEqual(Agent.authorize('non-existent token'), None)

        # Test delete method
        self.assertTrue(Agent.get(name=agent.name).delete())
        self.assertRaises(AttributeError, lambda: Agent.get(
            name='non-existent agent').delete())
        self.assertEqual(Agent.get(), None)

        self.assertEqual(Agent.count(),
                         agents_before + 2)
        self.assertEqual(AgentAuthToken.count(),
                         agent_tokens_before + 2)
        self.assertEqual(AgentDetail.count(),
                         agent_details_before)

    def test_agent_detail(self):
        agent = Agent(name='Agent')
        models.session.add(agent)
        models.session.commit()

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
        self.assertEqual(
            agent.detail.id, AgentDetail.detail_for_agent_id(agent.id).id)
