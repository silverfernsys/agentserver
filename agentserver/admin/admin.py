#! /usr/bin/env python
from agentserver.db import dal, User, Agent, UserAuthToken, AgentAuthToken
from agentserver.admin.config import config
from agentserver.utils import haiku
from datetime import datetime

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

        print('Successfully created user {email}.'.format(email=user.email))

    def auth_admin(self, session):
        while True:
            input_email = raw_input('Enter admin email address: ')
            admin_user = session.query(User).filter(User.email == input_email).first()
            if admin_user and admin_user.is_admin:
                break
            else:
                print('{email} is not an admin email address...'.format(email=input_email))
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
            print('Successfully deleted {email}.'.format(email=delete_email))
        except Exception as e:
            print('Could not find {email}.'.format(email=delete_email))

    def list_users(self):
        print("{name}{email}{admin}{created}".format(
            name="Name".ljust(70),
            email="Email".ljust(30),
            admin="Admin".ljust(10),
            created="Created"))
        for user in dal.Session().query(User):
            if user.is_admin:
                admin_str = 'Y'
            else:
                admin_str = 'N'
            line = "{name}{email}{admin}{created}".format(
                name=user.name.ljust(70),
                email=user.email.ljust(30),
                admin=admin_str.ljust(10),
                created=user.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

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
                print('Token {token} created for {email}.'.format(token=user_token.uuid, email=input_email))
            except:
                print('A token already exists for {email}. Doing nothing.'.format(email=input_email))
        except Exception as e:
            print('User {email} does not exist.'.format(email=input_email))
            print('Details: {details}'.format(details=str(e)))

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
                print('Successfully deleted token for {email}.'.format(email=input_email))
            except:
                print('No token exists for {email}'.format(email=input_email))
        except Exception as e:
            print('User {email} does not exist.'.format(email=input_email))
            print('Details: {details}'.format(details=str(e)))

    def list_user_auth_tokens(self):
        print("{email}{token}{created}".format(
            email="Email".ljust(30),
            token="Token".ljust(70),
            created="Created"))
        for token in dal.Session().query(UserAuthToken):
            line = "{email}{token}{created}".format(
                email=token.user.email.ljust(30),
                token=token.uuid.ljust(70),
                created=token.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def generate_agent_name(self):
        h = haiku()
        num_haikus = str(dal.Session().query(Agent).filter(Agent.name.like('{haiku}%'.format(haiku=h))).count())
        return '{haiku}-{num}'.format(haiku=h, num=num_haikus.ljust(4,'0'))

    def create_agent(self):
        session = dal.Session()
        print('Create agent: please authenticate...')
        self.auth_admin(session)

        name = raw_input('Enter agent name[Press ENTER to autogenerate]: ')
        if len(name) == 0:
            name = self.generate_agent_name()

        agent = Agent(name=name)
        session.add(agent)
        session.commit()

        print('Successfully created agent {name}'.format(name=agent.name))

    def delete_agent(self):
        session = dal.Session()
        print('Delete agent: please authenticate...')
        self.auth_admin(session)

        input_id = raw_input('Enter agent id: ')

        try:
            agent = session.query(Agent).filter(Agent.id == input_id).one()
            # Delete timeseries data here!
            session.delete(agent)
            session.commit()
            print('Successfully deleted agent %s' % input_ip)
        except:
            print('Agent does not exist.')

    def list_agents(self):
        print("{id}{name}{created}".format(id="id".ljust(30), name="Name".ljust(30), created="Created"))
        for agent in dal.Session().query(Agent):
            line = "{id}{name}{created}".format(id=str(agent.id).ljust(30), name=agent.name.ljust(30),
                created=agent.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def create_agent_auth_token(self):
        session = dal.Session()
        print('Create agent token: please authenticate...')
        self.auth_admin(session)

        input_id = raw_input('Enter id of agent to create token for: ')
        try:
            agent = session.query(Agent).filter(Agent.id == input_id).one()
            token = AgentAuthToken(agent=agent)
            try:
                session.add(token)
                session.commit()
                print(str('Token {token} created for {id}. {name}'
                    .format(token=token.uuid, id=agent.id,
                        name=agent.name)))
            except:
                print('A token already exists for {id}. {name}. Doing nothing.'
                    .format(id=agent.id, name=agent.name))
        except Exception as e:
            print('Agent {id} does not exist.'.format(id=input_id))
            print('Details: {details}'.format(details=str(e)))

    def delete_agent_auth_token(self):
        session = dal.Session()
        print('Delete agent token: please authenticate...')
        self.auth_admin(session)
        input_id = raw_input('Enter id of agent to delete token for: ')
        try:
            agent = session.query(Agent).filter(Agent.id == input_id).one()
            try:
                token = session.query(AgentAuthToken).filter(AgentAuthToken.agent == agent).one()
                session.delete(token)
                session.commit()
                print('Successfully deleted token for {id}. {name}'.format(id=agent.id, name=agent.name))
            except:
                print('No token exists for {id}'.format(id=input_id))
        except Exception as e:
            print('Agent {id} does not exist.'.format(id=input_id))
            print('Details: {details}'.format(details=str(e)))

    def list_agent_auth_tokens(self):
        print("{created}{id}{name}{token}".format(
            created="Created".ljust(30),
            id="id".ljust(30),
            name="Name".ljust(30),
            token="Token".ljust(70)))
        for token in dal.Session().query(AgentAuthToken):
            line = "{created}{id}{name}{token}".format(
                created=token.created_on.strftime('%d-%m-%Y %H:%M:%S').ljust(30),
                id=str(token.agent.id).ljust(30),
                name=token.agent.name.ljust(30),
                token=token.uuid.ljust(70))
            print(line)
