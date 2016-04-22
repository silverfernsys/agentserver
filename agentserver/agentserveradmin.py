#! /usr/bin/env python
import argparse
import logging
import signal
import sys
import time
import ConfigParser
from setproctitle import setproctitle
from admin.admin import Admin
from admin.config import config

def main():
    setproctitle('agentserveradmin')
    parser = argparse.ArgumentParser()
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

    # try:
    config.resolveArgs(args)
    if config.isResolved():
        logging.basicConfig(filename=config.log_file, format='%(asctime)s::%(levelname)s::%(name)s::%(message)s', level=logging.DEBUG)
        
        admin = Admin()

        if args.subparser_name == 'create_user':
            admin.create_user()
        elif args.subparser_name == 'delete_user':
            admin.delete_user()
        elif args.subparser_name == 'list_users':
            admin.list_users()
        elif args.subparser_name == 'create_user_auth_token':
            admin.create_user_auth_token()
        elif args.subparser_name == 'delete_user_auth_token':
            admin.delete_user_auth_token()
        elif args.subparser_name == 'list_user_auth_tokens':
            admin.list_user_auth_tokens()
        elif args.subparser_name == 'create_agent':
            admin.create_agent()
        elif args.subparser_name == 'delete_agent':
            admin.delete_agent()
        elif args.subparser_name == 'list_agents':
            admin.list_agents()
        elif args.subparser_name == 'create_agent_auth_token':
            admin.create_agent_auth_token()
        elif args.subparser_name == 'delete_agent_auth_token':
            admin.delete_agent_auth_token()
        elif args.subparser_name == 'list_agent_auth_tokens':
            admin.list_agent_auth_tokens()
    else:
        sys.stderr.write('ERROR: resolving configuration.\n')
        sys.exit(1)


if __name__ == "__main__":
    main()