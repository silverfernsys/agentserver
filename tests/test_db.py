#! /usr/bin/env python
import unittest
from datetime import datetime
# from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from db import (dal, User, UserAuthToken, Agent, AgentAuthToken,
    ProcessDetail, ProcessState)


class TestDb(unittest.TestCase):
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

    def test_agents_and_agent_tokens(self):
        # Generate agents and tokens
        dal.session.add_all([
            AgentAuthToken(agent=Agent(name='Agent 0')),
            AgentAuthToken(agent=Agent(name='Agent 1')),
            AgentAuthToken(agent=Agent(name='Agent 2'))])
        dal.session.commit()

    def test_process_detail(self):
        agent = Agent(name='Agent')
        dal.session.add(agent)
        dal.session.commit()

        detail_count = dal.session.query(ProcessDetail).count()

        detail_0_start_before = datetime(2016, 1, 14, 11, 30)
        detail_1_start_before = datetime(2016, 1, 14, 12, 30)
        detail_0 = ProcessDetail.update_or_create('process_0', agent.id, detail_0_start_before)
        detail_1 = ProcessDetail.update_or_create('process_1', agent.id, detail_1_start_before)

        self.assertEqual(dal.session.query(ProcessDetail).count(), detail_count + 2)

        detail_0_start_after = datetime(2016, 2, 14, 11, 30)
        detail_1_start_after = datetime(2016, 1, 13, 12, 30)
        ProcessDetail.update_or_create('process_0', agent.id, detail_0_start_after)
        ProcessDetail.update_or_create('process_1', agent.id, detail_1_start_after)

        self.assertEqual(dal.session.query(ProcessDetail).count(), detail_count + 2)
        
        self.assertNotEqual(detail_0.id, detail_1.id)
        self.assertEqual(detail_0.start, detail_0_start_after)
        self.assertEqual(detail_1.start, detail_1_start_after)

    def test_process_state(self):
        agent = Agent(name='Agent 100')
        dal.session.add(agent)
        dal.session.commit()

        for i in range(4):
            dal.session.add(ProcessDetail.update_or_create('process_{0}'.format(i),
                agent.id, datetime.now()))

        details = agent.processdetails
        self.assertEqual(len(details), 4)

        for i in range(4):
            for detail in details:
                dal.session.add(ProcessState(detail_id=detail.id,
                    name='state_{0}_{1}'.format(detail.name, i)))
        dal.session.commit()

        print(dal.session.query(ProcessState).count())
        # states = dal.session.query(ProcessState).filter(ProcessState.detail.agent == agent).all()
        # print(len(states))
        # self.assertEqual()














