from __future__ import absolute_import
from os.path import dirname, join, expanduser
from config.base import Config


class AdminConfig(Config):
    possible_args = [
        ('log_level', str),
        ('log_file', str),
        ('database', str)
    ]

    config_search_paths = [
        join(dirname(__file__), 'agentserver.conf'),
        expanduser('~/agentserver.conf'),
        '/etc/agentserver/agentserver.conf'
    ]

    config_name = 'agentserver'

    def config_parser(self, parser):
        choices = ['DEBUG', 'INFO', 'WARNING',
                   'ERROR', 'CRITICAL']

        subparsers = parser.add_subparsers(
            title='available commands', help='command help',
            dest='command', metavar='')

        subparsers.add_parser(name='create_user',
                              help='create new user')
        subparsers.add_parser(name='delete_user',
                              help='delete existing user')
        subparsers.add_parser(name='list_users',
                              help='list users')
        subparsers.add_parser(name='create_user_auth_token',
                              help='create user authentication token')
        subparsers.add_parser(name='delete_user_auth_token',
                              help='delete user authentication token')
        subparsers.add_parser(name='list_user_auth_tokens',
                              help='list user authentication tokens')
        subparsers.add_parser(name='create_agent',
                              help='create new agent')
        subparsers.add_parser(name='delete_agent',
                              help='delete existing agent')
        subparsers.add_parser(name='list_agents',
                              help='list agents')
        subparsers.add_parser(name='create_agent_auth_token',
                              help='create agent authentication token')
        subparsers.add_parser(name='delete_agent_auth_token',
                              help='delete agent authentication token')
        subparsers.add_parser(name='list_agent_auth_tokens',
                              help='list agent authentication tokens')

        for subparser in subparsers.choices.values():
            subparser.add_argument('--config',
                                   help='path to the configuration file.')
            subparser.add_argument('--log_level', choices=choices,
                                   help='log level') #, metavar='asdf')
            subparser.add_argument('--log_file', help='log file path')
            subparser.add_argument('--database', help='url to database')


config = AdminConfig()
