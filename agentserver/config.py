import ConfigParser

class Config(object):
    possible_args = [
    'log_level',
    'log_file',
    'database',
    'timeseries',
    'port',
    'max_wait_seconds_before_shutdown',
    'flush_data_period',
    'push_data_period',
    ]

    def __init__(self):
        self.loadConfig('/etc/agentserver/agentserver.conf')

    def loadConfig(self, path):
        try:
            config_parser = ConfigParser.ConfigParser()
            config_parser.read(path)
            data = {p: config_parser.get('agentserver', p) for p in Config.possible_args}
            self.__dict__.update(data)
        except:
            print('Error loading configuration file at %s.' % path)

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

config = Config()
