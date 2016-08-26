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

    def __init__(self):
        self.loadConfig(self.config_search_paths)
        self.initLogging()

    def loadConfig(self, paths):
        try:
            parser = ArgumentParser()
            parser.add_argument("--config", help="configuration file to read")
            parser.add_argument("--log_level", help="log level")
            parser.add_argument("--log_file", help="log file path")
            parser.add_argument("--database", help="the database connection protocol://username:password@host:port/dbname")
            parser.add_argument("--kafka", help="the kafka queue host:port")
            parser.add_argument("--druid", help="the druid broker host:port")
            parser.add_argument("--max_wait_seconds_before_shutdown", help="the number of seconds to wait before shutting down server")
            parser.add_argument("--url", help="server url")
            parser.add_argument("--port", help="server port")
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
