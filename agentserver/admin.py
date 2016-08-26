#! /usr/bin/env python
from db.models import mal, User, Agent, UserAuthToken, AgentAuthToken
from config.admin import config
from utils.haiku import haiku_name
from datetime import datetime
from setproctitle import setproctitle

import getpass

class Admin(object):
    def __init__(self, config):
        setproctitle('agentserveradmin')
        print('Connecting to database...')
        self.config = config
        self.config.parse()
        mal.connect(conn_string=config.database)

    def run(self):
        command = getattr(self, self.config.command)
        command()

    def create_user(self):
        while True:
            email = raw_input('Enter email address: ')
            if User.get(email=email):
                print('Email already exists. Use another email address.')
            else:
                break

        name = raw_input('Enter display name: ')

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

        user = User(name=name,
                     email=email,
                     is_admin=is_admin,
                     password=password_1).save()

        print('Successfully created user {email}.'.format(email=user.email))

    def auth_admin(self):
        while True:
            email = raw_input('Enter admin email address: ')
            user = User.get(email=email)
            if user and user.is_admin:
                break
            else:
                print('{email} is not an admin email address...'.format(email=email))
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
        try:
            User.get(email=email).delete()
            print('Successfully deleted {email}.'.format(email=email))
        except:
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
        email = raw_input('Enter email to create a token for: ')
        user = User.get(email=email)
        if user:
            try:
                token = UserAuthToken(user=user).save()
                print('Token {token} created for {email}.'.format(token=token.uuid, email=email))
            except:
                print('A token already exists for {email}. Doing nothing.'.format(email=email))
        else:
            print('User {email} does not exist.'.format(email=email))

    def delete_user_auth_token(self):
        print('Delete token: please authenticate...')
        self.auth_admin()
        email = raw_input('Enter email to delete token for: ')
        user = User.get(email=email)
        if user:
            try:
                user.token.delete()
                print('Successfully deleted token for {email}.'.format(email=email))
            except:
                print('No token exists for {email}'.format(email=email))
        else:
            print('User {email} does not exist.'.format(email=email))

    def list_user_auth_tokens(self):
        print("{email}{token}{created}".format(
            email="Email".ljust(30),
            token="Token".ljust(70),
            created="Created"))
        for token in UserAuthToken.all():
            line = "{email}{token}{created}".format(
                email=token.user.email.ljust(30),
                token=token.uuid.ljust(70),
                created=token.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def create_agent(self):
        print('Create agent: please authenticate...')
        self.auth_admin()

        name = raw_input('Enter agent name[Press ENTER to autogenerate]: ')
        if len(name) == 0:
            name = haiku_name(Agent.count())

        agent = Agent(name=name).save()
        print('Successfully created agent {name}'.format(name=agent.name))

    def delete_agent(self):
        print('Delete agent: please authenticate...')
        self.auth_admin()
        name = raw_input('Enter agent name: ')
        if Agent.get(name=name).delete():
            print('Successfully deleted agent %s' % name)
        else:
            print('Agent does not exist.')

    def list_agents(self):
        print("{id}{name}{created}".format(id="id".ljust(30), name="Name".ljust(30), created="Created"))
        for agent in Agent.all():
            line = "{id}{name}{created}".format(id=str(agent.id).ljust(30), name=agent.name.ljust(30),
                created=agent.created_on.strftime('%d-%m-%Y %H:%M:%S'))
            print(line)

    def create_agent_auth_token(self):
        print('Create agent token: please authenticate...')
        self.auth_admin()

        id = raw_input('Enter id of agent to create token for: ')
        try:
            agent = Agent.get(id=id)
            try:
                token = AgentAuthToken(agent=agent).save()
                print(str('Token {token} created for {id}. {name}'
                    .format(token=token.uuid, id=agent.id,
                        name=agent.name)))
            except:
                print('A token already exists for {id}. {name}. Doing nothing.'
                    .format(id=agent.id, name=agent.name))
        except Exception as e:
            print('Agent {id} does not exist.'.format(id=id))
            print('Details: {details}'.format(details=str(e)))

    def delete_agent_auth_token(self):
        print('Delete agent token: please authenticate...')
        self.auth_admin()
        id = raw_input('Enter name of agent to delete token for: ')
        try:
            agent = Agent.get(id=id)
            try:
                agent.token.delete()
                print('Successfully deleted token for {id}. {name}'.format(id=agent.id, name=agent.name))
            except:
                print('No token exists for {id}'.format(id=id))
        except Exception as e:
            print('Agent {id} does not exist.'.format(id=id))
            print('Details: {details}'.format(details=str(e)))

    def list_agent_auth_tokens(self):
        print("{created}{id}{name}{token}".format(
            created="Created".ljust(30),
            id="id".ljust(30),
            name="Name".ljust(30),
            token="Token".ljust(70)))
        for token in AgentAuthToken.all():
            line = "{created}{id}{name}{token}".format(
                created=token.created_on.strftime('%d-%m-%Y %H:%M:%S').ljust(30),
                id=str(token.agent.id).ljust(30),
                name=token.agent.name.ljust(30),
                token=token.uuid.ljust(70))
            print(line)


def main():
    Admin(config).run()


if __name__ == "__main__":
    main()
