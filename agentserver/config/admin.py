import sys, logging
from ConfigParser import SafeConfigParser
from argparse import ArgumentParser
from os.path import dirname, join, expanduser


log_vals = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING, 
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG, 
    'NOTSET': logging.NOTSET }


class Config(object):
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

    def __init__(self):
        self.loadConfig(self.config_search_paths)
        self.initLogging()

    def loadConfig(self, paths):
        try:
            parser = ArgumentParser()
            subparsers = parser.add_subparsers(help="sub-command help", dest="subparser_name")

            create_user = subparsers.add_parser('create_user', help='create new user')
            create_user.add_argument("--config", help="path to the configuration file.")
            create_user.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            create_user.add_argument("--log_file", help="log file path")
            create_user.add_argument("--database", help="url to database")

            delete_user = subparsers.add_parser('delete_user', help='delete existing user')
            delete_user.add_argument("--config", help="path to the configuration file.")
            delete_user.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            delete_user.add_argument("--log_file", help="log file path")
            delete_user.add_argument("--database", help="url to database")

            list_users = subparsers.add_parser('list_users', help='list users')
            list_users.add_argument("--config", help="path to the configuration file.")
            list_users.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            list_users.add_argument("--log_file", help="log file path")
            list_users.add_argument("--database", help="url to database")

            create_user_auth_token = subparsers.add_parser('create_user_auth_token', help='create user authentication token')
            create_user_auth_token.add_argument("--config", help="path to the configuration file.")
            create_user_auth_token.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            create_user_auth_token.add_argument("--log_file", help="log file path")
            create_user_auth_token.add_argument("--database", help="url to database")

            delete_user_auth_token = subparsers.add_parser('delete_user_auth_token', help='delete user authentication token')
            delete_user_auth_token.add_argument("--config", help="path to the configuration file.")
            delete_user_auth_token.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            delete_user_auth_token.add_argument("--log_file", help="log file path")
            delete_user_auth_token.add_argument("--database", help="url to database")

            list_user_auth_tokens = subparsers.add_parser('list_user_auth_tokens', help='list user authentication tokens')
            list_user_auth_tokens.add_argument("--config", help="path to the configuration file.")
            list_user_auth_tokens.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            list_user_auth_tokens.add_argument("--log_file", help="log file path")
            list_user_auth_tokens.add_argument("--database", help="url to database")

            create_agent = subparsers.add_parser('create_agent', help='create new agent')
            create_agent.add_argument("--config", help="path to the configuration file.")
            create_agent.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            create_agent.add_argument("--log_file", help="log file path")
            create_agent.add_argument("--database", help="url to database")

            delete_agent = subparsers.add_parser('delete_agent', help='delete existing agent')
            delete_agent.add_argument("--config", help="path to the configuration file.")
            delete_agent.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            delete_agent.add_argument("--log_file", help="log file path")
            delete_agent.add_argument("--database", help="url to database")

            list_agents = subparsers.add_parser('list_agents', help='list agents')
            list_agents.add_argument("--config", help="path to the configuration file.")
            list_agents.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            list_agents.add_argument("--log_file", help="log file path")
            list_agents.add_argument("--database", help="url to database")

            create_agent_auth_token = subparsers.add_parser('create_agent_auth_token', help='create agent authentication token')
            create_agent_auth_token.add_argument("--config", help="path to the configuration file.")
            create_agent_auth_token.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            create_agent_auth_token.add_argument("--log_file", help="log file path")
            create_agent_auth_token.add_argument("--database", help="url to database")

            delete_agent_auth_token = subparsers.add_parser('delete_agent_auth_token', help='delete agent authentication token')
            delete_agent_auth_token.add_argument("--config", help="path to the configuration file.")
            delete_agent_auth_token.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            delete_agent_auth_token.add_argument("--log_file", help="log file path")
            delete_agent_auth_token.add_argument("--database", help="url to database")

            list_agent_auth_tokens = subparsers.add_parser('list_agent_auth_tokens', help='list agent authentication tokens')
            list_agent_auth_tokens.add_argument("--config", help="path to the configuration file.")
            list_agent_auth_tokens.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="log level")
            list_agent_auth_tokens.add_argument("--log_file", help="log file path")
            list_agent_auth_tokens.add_argument("--database", help="url to database")

            args = parser.parse_args()

            config_parser = SafeConfigParser()
            if args.config:
                paths = [args.config]
            else:
                paths = self.config_search_paths

            config_parser.read(paths)

            data = {p: f(getattr(args, p, None) or config_parser.get('agentserver', p)) for (p, f) in self.possible_args}

            for (arg, _type) in self.possible_args:
                if arg not in data:
                    print('Missing configuration argument {0}. Exiting.\n'.format(arg))
                    sys.exit(1)

            data['command'] = args.subparser_name

            self.__dict__.update(data)
        except Exception as e:
            print('Error loading configuration files at {0}.\nEXCEPTION DETAILS: {1}'.format(paths, e))

    def initLogging(self):
        logging.basicConfig(filename=self.log_file,
            format='%(asctime)s::%(levelname)s::%(name)s::%(message)s',
            level=log_vals.get(self.log_level, logging.DEBUG))

    def __repr__(self):
        return '<Config({0}>'.format(', '.join('%s=%r' % (k, v)
            for (k, v) in self.__dict__.iteritems()))


config = Config()
