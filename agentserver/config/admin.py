from os.path import dirname, join, expanduser
from configutil import Config

config = Config()
config.add_paths([join(dirname(__file__), 'agentserver.conf'),
    expanduser('~/.agentserver/agentserver.conf'),
    '/etc/agentserver/agentserver.conf'
])

section = config.add_section('agentserver')
section.add_argument('log_level', 'log level',
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
section.add_argument('log_file', 'log file path')
section.add_argument('database', 'url to database')

config.add_command(name='create_user', help='create new user')
config.add_command(name='delete_user', help='delete existing user')
config.add_command(name='list_users', help='list users')
config.add_command(name='create_user_auth_token', help='create user authentication token')
config.add_command(name='delete_user_auth_token', help='delete user authentication token')
config.add_command(name='list_user_auth_tokens', help='list user authentication tokens')
config.add_command(name='create_agent', help='create new agent')
config.add_command(name='delete_agent', help='delete existing agent')
config.add_command(name='list_agents', help='list agents')
config.add_command(name='create_agent_auth_token', help='create agent authentication token')
config.add_command(name='delete_agent_auth_token', help='delete agent authentication token')
config.add_command(name='list_agent_auth_tokens', help='list agent authentication tokens')
