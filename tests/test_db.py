#! /usr/bin/env python
import unittest
from datetime import datetime
# from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from db import (dal, User, UserAuthToken, Agent, AgentAuthToken,
    ProcessDetail, ProcessState, StateEnum)


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

        for detail in details:
            for i in range(4):
                dal.session.add(ProcessState(detail_id=detail.id,
                    name=StateEnum.STARTING))
        dal.session.commit()

        print(dal.session.query(ProcessState).count())

        details = agent.process_states()
        print(details)


        # states = dal.session.query(ProcessState).join(ProcessDetail).filter(ProcessDetail.agent_id == agent.id).all()
        # dal.session.query(ProcessDetail).filter(ProcessDetail.agent_id == agent.id)
        # print(states)
        # states = dal.session.query(ProcessState).filter(ProcessState.detail.agent == agent).all()
        # print(len(states))
        # self.assertEqual()














