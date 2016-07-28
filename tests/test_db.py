#! /usr/bin/env python
import unittest
from decimal import Decimal
from db import dal, User, UserAuthToken, Agent, AgentAuthToken


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dal.connect('sqlite:///:memory:')
        dal.session = dal.Session()

    def setUp(self):
        dal.session = dal.Session()

    def tearDown(self):
        dal.session.rollback()
        dal.session.close()

    def test_users_and_user_tokens(self):
        # Generate users
        user_0 = User(name='Marc Wilson',
                         email='marcw@silverfern.io',
                         is_admin=True,
                         password='asdf')
        user_1 = User(name='Phil Lake',
                         email='philip@gmail.com',
                         is_admin=False,
                         password='asdf')
        user_2 = User(name='Colin Ng',
                         email='colin@ngland.net',
                         is_admin=True,
                         password='asdf')

        # Generate user tokens
        u_token_0 = UserAuthToken(user=user_0)
        u_token_1 = UserAuthToken(user=user_1)
        u_token_2 = UserAuthToken(user=user_2)
        dal.session.add(u_token_0)
        dal.session.add(u_token_1)
        dal.session.add(u_token_2)
        # dal.session.bulk_save_objects([u_token_0, u_token_1, u_token_2])
        dal.session.commit()

    def test_agents_and_agent_tokens(self):
        # Generate agents
        agent_0 = Agent(name='Agent 1')
        agent_1 = Agent(name='Agent 2')
        agent_2 = Agent(name='Agent 3')

        # Generate agent tokens
        a_token_0 = AgentAuthToken(agent=agent_0)
        a_token_1 = AgentAuthToken(agent=agent_1)
        a_token_2 = AgentAuthToken(agent=agent_2)
        dal.session.add(a_token_0)
        dal.session.add(a_token_1)
        dal.session.add(a_token_2)
        dal.session.commit()
