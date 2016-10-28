#! /usr/bin/env python
import getpass
import sys

from configutil import ConfigError
from setproctitle import setproctitle
from tabulate import tabulate
from termcolor import colored
from agentserver.config.admin import config
from agentserver.db.models import models, User, Agent, UserAuthToken, AgentAuthToken
from agentserver.utils.haiku import haiku_name


HEADER_COLOR = None # 'green', 'red', etc


def color_text(text, color=None):
        return colored(text, color=color, attrs=['bold'])


class Admin(object):

    def __init__(self, config):
        setproctitle('agentserveradmin')
        self.config = config
        try:
            self.config.parse()
        except ConfigError as e:
            print('{0} Exiting.\n'.format(e.message))
            sys.exit(1)
        print('Connecting to database...')
        self.connect(config.arguments.agentserver.database)

    def run(self):
        command = getattr(self, self.config.arguments.command)
        command()

    def connect(self, uri):
        try:
            models.connect(conn_string=uri)
        except Exception as e:
            print(e.message)
            sys.exit(1)

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

        user = User(name=name, email=email, is_admin=is_admin,
                    password=password_1).save()

        print('Successfully created user {email}.'.format(email=user.email))

    def auth_admin(self):
        while True:
            email = raw_input('Enter admin email address: ')
            user = User.get(email=email)
            if user and user.is_admin:
                break
            else:
                print('{email} is not an admin email address...'
                      .format(email=email))
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
        table = [[user.name, user.email, user.admin, user.created]
                 for user in User.all()]
        print(tabulate(table, headers=self.bold_headers(
            ['Name', 'Email', 'Admin', 'Created']), tablefmt='plain'))

    def create_user_auth_token(self):
        print('Create token: please authenticate...')
        self.auth_admin()
        email = raw_input('Enter email to create a token for: ')
        user = User.get(email=email)
        if user:
            try:
                token = UserAuthToken(user=user).save()
                print('Token {token} created for {email}.'
                      .format(token=token.uuid, email=email))
            except:
                print('A token already exists for {email}. Doing nothing.'
                      .format(email=email))
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
                print('Successfully deleted token for {email}.'
                      .format(email=email))
            except:
                print('No token exists for {email}'.format(email=email))
        else:
            print('User {email} does not exist.'.format(email=email))

    def list_user_auth_tokens(self):
        table = [[token.user.email, token.uuid, token.created]
                 for token in UserAuthToken.all()]
        print(tabulate(table, headers=self.bold_headers(
            ['Email', 'Token', 'Created']), tablefmt='plain'))

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
        table = [[agent.name, agent.id, agent.created]
                 for agent in Agent.all()]
        print(tabulate(table, headers=self.bold_headers(
            ['Name', 'id', 'Created']), tablefmt='plain'))

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
                print('Successfully deleted token for {id}. {name}'
                      .format(id=agent.id, name=agent.name))
            except:
                print('No token exists for {id}'.format(id=id))
        except Exception as e:
            print('Agent {id} does not exist.'.format(id=id))
            print('Details: {details}'.format(details=str(e)))

    def list_agent_auth_tokens(self):
        table = [[token.agent.name, token.agent.id, token.uuid, token.created]
                 for token in AgentAuthToken.all()]
        headers = self.bold_headers(['Name', 'id', 'Token', 'Created'])
        print(tabulate(table, headers=headers, tablefmt='plain'))

    def bold_headers(self, headers):
        return [color_text(h, color=HEADER_COLOR) for h in headers]


def main():
    Admin(config).run()


if __name__ == "__main__":
    main()
