import ConfigParser

class Config(object):
    _Instance = None

    def __init__(self):
        self.data = {}

    def resolveArgs(self, args):
        self.data.update(self._resolveArgs(args))

    def _resolveArgs(self, args):
        """
        Returns a dictionary consisting of keys found
        in config and the values of config overwritten
        by values of args
        """
        data = {}
        try:
            config_parser = ConfigParser.ConfigParser()
            config_file_path = args.config or '/etc/agentserver/agentserver.conf'
            config_parser.read(config_file_path)
            try:
                data['log_level'] = args.log_level or config_parser.get('agentserver', 'log_level')
            except:
                data['log_level'] = config_parser.get('agentserver', 'log_level')
            try:
                data['log_file'] = args.log_file or config_parser.get('agentserver', 'log_file')
            except:
                data['log_file'] = config_parser.get('agentserver', 'log_file')
            try:
                data['database'] = args.database or config_parser.get('agentserver', 'database')
            except:
                data['database'] = config_parser.get('agentserver', 'database')
            try:
                data['timeseries'] = args.timeseries or config_parser.get('agentserver', 'timeseries')
            except:
                data['timeseries'] = config_parser.get('agentserver', 'timeseries')
            try:
                data['port'] = args.port or config_parser.getint('agentserver', 'port')
            except:
                data['port'] = config_parser.getint('agentserver', 'port')
            try:
                data['max_wait_seconds_before_shutdown'] = args.max_wait_seconds_before_shutdown or config_parser.getint('agentserver', 'max_wait_seconds_before_shutdown')
            except:
                data['max_wait_seconds_before_shutdown'] = config_parser.getint('agentserver', 'max_wait_seconds_before_shutdown')
            try:
                data['flush_data_period'] = args.flush_data_period or config_parser.getint('agentserver', 'flush_data_period')
            except:
                data['flush_data_period'] = config_parser.getint('agentserver', 'flush_data_period')
            try:
                data['push_data_period'] = args.flush_data_period or config_parser.getint('agentserver', 'push_data_period')
            except:
                data['push_data_period'] = config_parser.getint('agentserver', 'push_data_period')
        except:
            print('Error loading configuration file at %s.' % config_file_path)
            data = {}
        return data

config = Config()
