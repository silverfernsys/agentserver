import sys
from ConfigParser import SafeConfigParser
from os.path import dirname, join, expanduser

class Config(object):
    possible_args = [
    'log_level',
    'log_file',
    'database',
    'kafka',
    'druid',
    'port',
    'max_wait_seconds_before_shutdown',
    'flush_data_period',
    'push_data_period',
    ]

    INSTALL_DIR = dirname(__file__)

    def __init__(self):
        self.loadConfig([
            join(Config.INSTALL_DIR, 'agentserver.conf'),
            expanduser('~/agentserver.conf'),
            '/etc/agentserver/agentserver.conf'])

    def loadConfig(self, paths):
        try:
            config_parser = SafeConfigParser()
            config_parser.read(paths)
            data = {p: config_parser.get('agentserver', p) for p in Config.possible_args}
            self.__dict__.update(data)
        except Exception as e:
            print('Error loading configuration file at %s.\nEXCEPTION DETAILS: %s' % (paths, e))

    def resolveArgs(self, args):
        """
        Returns a dictionary consisting of keys found
        in config and the values of config overwritten
        by values of args
        """
        if args.config:
            self.loadConfig(args.config)

        data = {p: getattr(args, p, None) for p in Config.possible_args if hasattr(args, p) and getattr(args, p, None) != None}

        self.__dict__.update(data)

    def isResolved(self):
        for arg in Config.possible_args:
            if arg not in self.__dict__:
                return False
        return True

config = Config()
