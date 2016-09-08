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
section.add_argument('kafka', help='the kafka queue host:port')
section.add_argument('druid', help='the druid broker host:port')
section.add_argument('port', help='port to run server on', type=int)
section.add_argument('max_wait_seconds_before_shutdown',
    help='the number of seconds to wait before shutting down server', type=float)
section.add_argument('flush_data_period', help='how often to flush data to druid', type=float)
section.add_argument('push_data_period', help='how often to push data to clients', type=float)
