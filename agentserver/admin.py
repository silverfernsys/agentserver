#! /usr/bin/env python
from db import dal, tal, prep_db, User, Agent, UserAuthToken, AgentAuthToken
from datetime import datetime
from config import config
import getpass


class Admin(object):
    def __init__(self):
        print('Connecting to database...')
        dal.connect(conn_string=config.database)

    def create_user(self):
        session = dal.Session()
        while True:
            input_email = raw_input('Enter email address: ')
            existing_user = session.query(User).filter(User.email == input_email).first()
            if existing_user:
                print('Email already exists. Use another email address.')
            else:
                break

        input_name = raw_input('Enter display name: ')

        while True:
            input_is_admin = raw_input('Admininstrative user? (y/N): ')
            if (len(input_is_admin) == 0) or (input_is_admin.upper() == 'N'):
                is_admin = False
                break
            elif input_is_admin.upper() == 'Y':
                is_admin = True
                break
        while True:
            password_1 = getpass.getpass('Enter password: ')
            password_2 = getpass.getpass('Re-enter password: ')
            if password_1 != password_2:
                print('Passwords do not match.')
            else:
                break

        user = User(name=input_name,
                     email=input_email,
                     is_admin=is_admin,
                     password=password_1)
        session.add(user)
        session.commit()

        print('Successfully created user %s' % user.email)

    def auth_admin(self, session):
        while True:
            input_email = raw_input('Enter admin email address: ')
            admin_user = session.query(User).filter(User.email == input_email).first()
            if admin_user and admin_user.is_admin:
                break
            else:
                print('%s is not an admin email address...' % input_email)
        while True:
            password = getpass.getpass('Enter password: ')
            if admin_user.authenticates(password):
                break
            else:
                print('Password incorrect. Please try again...')

    def delete_user(self):
        session = dal.Session()
        print('Delete user: please authenticate...')
        self.auth_admin(session)
        delete_email = raw_input('Enter email address of user to delete: ')

        try:
            delete_user = session.query(User).filter(User.email == delete_email).one()
            session.delete(delete_user)
            session.commit()
            print('Successfully deleted %s' % delete_email)
        except Exception as e:
            print('Could not find %s' % delete_email)

    def list_users(self):
        print("%s%s%sCreated" % ("Name".ljust(70), "Email".ljust(30), "Admin".ljust(10)))
        for user in dal.Session().query(User):
            if user.is_admin:
                admin_str = 'Y'
            else:
                admin_str = 'N'
            line = "%s%s%s%s" % (user.name.ljust(70), user.email.ljust(30), admin_str.ljust(10), user.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(str(line))

    def create_user_auth_token(self):
        session = dal.Session()
        print('Create token: please authenticate...')
        self.auth_admin(session)

        input_email = raw_input('Enter email to create a token for: ')
        try:
            input_user = session.query(User).filter(User.email == input_email).one()
            user_token = UserAuthToken(user=input_user)
            try:
                session.add(user_token)
                session.commit()
                print(str('Token %s created for %s' % (user_token.uuid, input_email)))
            except:
                print('A token already exists for %s. Doing nothing.' % input_email)
        except Exception as e:
            print('User %s does not exist.' % input_email)
            print('Details: %s' % e)

    def delete_user_auth_token(self):
        session = dal.Session()
        print('Delete token: please authenticate...')
        self.auth_admin(session)

        input_email = raw_input('Enter email to delete token for: ')
        try:
            input_user = session.query(User).filter(User.email == input_email).one()
            try:
                user_token = session.query(UserAuthToken).filter(UserAuthToken.user == input_user).one()
                session.delete(user_token)
                session.commit()
                print('Successfully deleted token for %s.' % input_email)
            except:
                print('No token exists for %s' % input_email)
        except Exception as e:
            print('User %s does not exist.' % input_email)
            print('Details: %s' % e)

    def list_user_auth_tokens(self):
        print("%s%sCreated" % ("Email".ljust(30), "Token".ljust(70)))
        for token in dal.Session().query(UserAuthToken):
            line = "%s%s%s" % (token.user.email.ljust(30), token.uuid.ljust(70), token.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(str(line))

    def create_agent(self):
        session = dal.Session()
        print('Create agent: please authenticate...')
        self.auth_admin(session)

        input_ip = raw_input('Enter agent ip address: ')
        while True:
            print('1) 3 days')
            print('2) 1 week')
            print('3) 3 weeks')
            print('4) 5 weeks')
            print('5) Infinite')
            input_retention_policy = int(raw_input('Select a retention policy:'))
            try:
                if (input_retention_policy - 1) in range(5):
                    break
                else:
                    pass
            except:
                pass
        if input_retention_policy == 1:
            retention_policy = '3d'
        elif input_retention_policy == 2:
            retention_policy = '1w'
        elif input_retention_policy == 3:
            retention_policy = '3w'
        elif input_retention_policy == 4:
            retention_policy = '5w'
        elif input_retention_policy == 5:
            retention_policy = 'INF'

        dbname = Agent.supervisor_database_name(input_ip)
        agent = Agent(ip=input_ip,
            retention_policy=retention_policy,
            timeseries_database_name=dbname)
        session.add(agent)
        session.commit()

        # Now create timeseries database.
        tal.connect(config.timeseries, dbname)
        conn = tal.connection(dbname)
        conn.create_database(dbname)

        policy_name = 'policy_{rt}'.format(rt=retention_policy)
        conn.create_retention_policy(policy_name, retention_policy, 3, default=True)
        print('Successfully created agent {ip}'.format(ip=agent.ip))

    def delete_agent(self):
        session = dal.Session()
        print('Delete agent: please authenticate...')
        self.auth_admin(session)

        input_ip = raw_input('Enter agent ip address: ')

        try:
            input_agent = session.query(Agent).filter(Agent.ip == input_ip).one()
            # Delete timeseries database.
            try:
                tal.connect(config.timeseries, input_agent.timeseries_database_name)
                conn = tal.connection(input_agent.timeseries_database_name)
                conn.drop_database(input_agent.timeseries_database_name)
            except Exception as e:
                print('Exception dropping timeseries database: %s' % e)
            session.delete(input_agent)
            session.commit()
            print('Successfully deleted agent %s' % input_ip)
        except:
            print('Agent does not exist.')

    def list_agents(self):
        print("%s%s%sCreated" % ("IP Address".ljust(30), "Retention Policy".ljust(30), "Timeseries".ljust(30)))
        for agent in dal.Session().query(Agent):
            line = "%s%s%s%s" % (agent.ip.ljust(30), agent.retention_policy.ljust(30),
                agent.timeseries_database_name.ljust(30), agent.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(str(line))

    def create_agent_auth_token(self):
        session = dal.Session()
        print('Create agent token: please authenticate...')
        self.auth_admin(session)

        input_ip = raw_input('Enter ip of agent to create token for: ')
        try:
            input_agent = session.query(Agent).filter(Agent.ip == input_ip).one()
            agent_token = AgentAuthToken(agent=input_agent)
            try:
                session.add(agent_token)
                session.commit()
                print(str('Token %s created for %s' % (agent_token.uuid, input_ip)))
            except:
                print('A token already exists for %s. Doing nothing.' % input_ip)
        except Exception as e:
            print('Agent %s does not exist.' % input_ip)
            print('Details: %s' % e)

    def delete_agent_auth_token(self):
        session = dal.Session()
        print('Delete agent token: please authenticate...')
        self.auth_admin(session)

        input_ip = raw_input('Enter ip of agent to delete token for: ')
        try:
            input_agent = session.query(Agent).filter(Agent.ip == input_ip).one()
            try:
                agent_token = session.query(AgentAuthToken).filter(AgentAuthToken.agent == input_agent).one()
                session.delete(agent_token)
                session.commit()
                print('Successfully deleted token for %s.' % input_ip)
            except:
                print('No token exists for %s' % input_ip)
        except Exception as e:
            print('Agent %s does not exist.' % input_ip)
            print('Details: %s' % e)

    def list_agent_auth_tokens(self):
        print("%s%sCreated" % ("Ip".ljust(30), "Token".ljust(70)))
        for token in dal.Session().query(AgentAuthToken):
            line = "%s%s%s" % (token.agent.ip.ljust(30), token.uuid.ljust(70), token.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(str(line))
