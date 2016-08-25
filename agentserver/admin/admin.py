from db.models import mal, User, Agent, UserAuthToken, AgentAuthToken
from config import config
from utils.haiku import haiku_name
from datetime import datetime

import getpass

class Admin(object):
    def __init__(self):
        print('Connecting to database...')
        mal.connect(conn_string=config.database)

    def create_user(self):
        while True:
            input_email = raw_input('Enter email address: ')
            if User.get(email=input_email):
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

        session = mal.session
        user = User(name=input_name,
                     email=input_email,
                     is_admin=is_admin,
                     password=password_1)
        session.add(user)
        session.commit()

        print('Successfully created user {email}.'.format(email=user.email))

    def auth_admin(self):
        while True:
            input_email = raw_input('Enter admin email address: ')
            user = User.get(email=input_email)
            if user and user.is_admin:
                break
            else:
                print('{email} is not an admin email address...'.format(email=input_email))
        while True:
            password = getpass.getpass('Enter password: ')
            if user.authenticates(password):
                break
            else:
                print('Password incorrect. Please try again...')

    def delete_user(self):
        print('Delete user: please authenticate...')
        self.auth_admin()
        email = raw_input('Enter email address of user to delete: ')
        if User.delete(email):
            print('Successfully deleted {email}.'.format(email=email))
        else:
            print('Could not find {email}.'.format(email=email))

    def list_users(self):
        print("{name}{email}{admin}{created}".format(
            name="Name".ljust(70),
            email="Email".ljust(30),
            admin="Admin".ljust(10),
            created="Created"))
        for user in User.all():
            line = "{name}{email}{admin}{created}".format(
                name=user.name.ljust(70),
                email=user.email.ljust(30),
                admin=user.admin.ljust(10),
                created=user.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def create_user_auth_token(self):
        print('Create token: please authenticate...')
        self.auth_admin()
        session = mal.session
        input_email = raw_input('Enter email to create a token for: ')
        input_user = User.get(email=input_email)
        if input_user:
            user_token = UserAuthToken(user=input_user)
            try:
                session.add(user_token)
                session.commit()
                print('Token {token} created for {email}.'.format(token=user_token.uuid, email=input_email))
            except:
                print('A token already exists for {email}. Doing nothing.'.format(email=input_email))
        else:
            print('User {email} does not exist.'.format(email=input_email))

    def delete_user_auth_token(self):
        print('Delete token: please authenticate...')
        self.auth_admin()
        input_email = raw_input('Enter email to delete token for: ')
        session = mal.session
        user = User.get(email=input_email)
        if user:
            try:
                user_token = session.query(UserAuthToken).filter(UserAuthToken.user == user).one()
                session.delete(user_token)
                session.commit()
                print('Successfully deleted token for {email}.'.format(email=input_email))
            except:
                print('No token exists for {email}'.format(email=input_email))
        else:
            print('User {email} does not exist.'.format(email=input_email))

    def list_user_auth_tokens(self):
        print("{email}{token}{created}".format(
            email="Email".ljust(30),
            token="Token".ljust(70),
            created="Created"))
        for token in mal.session.query(UserAuthToken):
            line = "{email}{token}{created}".format(
                email=token.user.email.ljust(30),
                token=token.uuid.ljust(70),
                created=token.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def create_agent(self):
        session = mal.session
        print('Create agent: please authenticate...')
        self.auth_admin()

        name = raw_input('Enter agent name[Press ENTER to autogenerate]: ')
        if len(name) == 0:
            name = haiku_name(Agent.count())

        agent = Agent(name=name)
        session.add(agent)
        session.commit()

        print('Successfully created agent {name}'.format(name=agent.name))

    def delete_agent(self):
        print('Delete agent: please authenticate...')
        self.auth_admin()
        name = raw_input('Enter agent name: ')
        if Agent.delete(name):
            print('Successfully deleted agent %s' % name)
        else:
            print('Agent does not exist.')

    def list_agents(self):
        print("{id}{name}{created}".format(id="id".ljust(30), name="Name".ljust(30), created="Created"))
        for agent in mal.session.query(Agent):
            line = "{id}{name}{created}".format(id=str(agent.id).ljust(30), name=agent.name.ljust(30),
                created=agent.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def create_agent_auth_token(self):
        session = mal.session
        print('Create agent token: please authenticate...')
        self.auth_admin()

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
        session = mal.session
        print('Delete agent token: please authenticate...')
        self.auth_admin()
        input_id = raw_input('Enter name of agent to delete token for: ')
        try:
            agent = session.query(Agent).filter(Agent.id == input_id).one()
            try:
                session.delete(agent.token)
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
        for token in mal.session.query(AgentAuthToken):
            line = "{created}{id}{name}{token}".format(
                created=token.created_on.strftime('%d-%m-%Y %H:%M:%S').ljust(30),
                id=str(token.agent.id).ljust(30),
                name=token.agent.name.ljust(30),
                token=token.uuid.ljust(70))
            print(line)
