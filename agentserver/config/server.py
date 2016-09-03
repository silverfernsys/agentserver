from __future__ import absolute_import
from os.path import dirname, join, expanduser
from config.base import Config


class ServerConfig(Config):
    possible_args = [
        ('log_level', str),
        ('log_file', str),
        ('database', str),
        ('kafka', str),
        ('druid', str),
        ('port', int),
        ('max_wait_seconds_before_shutdown',  float),
        ('flush_data_period', float),
        ('push_data_period', float)
    ]

    config_search_paths = [
        join(dirname(__file__), 'agentserver.conf'),
        expanduser('~/agentserver.conf'),
        '/etc/agentserver/agentserver.conf'
    ]

    config_name = 'agentserver'

    def config_parser(self, parser):
        parser.add_argument('--config', help='configuration file to read')
        parser.add_argument('--log_level', help='log level')
        parser.add_argument('--log_file', help='log file path')
        parser.add_argument('--database', help='the database connection '
                            'protocol://username:password@host:port/dbname')
        parser.add_argument('--kafka', help='the kafka queue host:port')
        parser.add_argument('--druid', help='the druid broker host:port')
        parser.add_argument('--max_wait_seconds_before_shutdown',
                            help='the number of seconds to wait '
                                 'before shutting down server')
        parser.add_argument('--url', help='server url')
        parser.add_argument('--port', help='server port')


config = ServerConfig()
