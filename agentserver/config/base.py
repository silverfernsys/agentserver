import sys, logging
from ConfigParser import SafeConfigParser
from argparse import ArgumentParser


log_vals = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING, 
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG, 
    'NOTSET': logging.NOTSET }


class Config(object):
    possible_args = None
    config_search_paths = None

    def __init__(self):
        if self.possible_args is None:
            raise AttributeError('missing possible_args definition')
        if self.config_search_paths is None:
            raise AttributeError('missing config_search_paths definition')

    def parse(self):
        self.parse_config(self.config_search_paths)
        self.init_logging()

    def config_parser(self, parser):
        raise NotImplemented('config_parser must be implemented')

    def parse_config(self, paths):
        try:
            parser = ArgumentParser()
            self.config_parser(parser)

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

            if hasattr(args, 'subparser_name'):
                data['command'] = args.subparser_name

            self.__dict__.update(data)
        except Exception as e:
            print('Error loading configuration files at {0}.\nEXCEPTION DETAILS: {1}'.format(paths, e))

    def init_logging(self):
        logging.basicConfig(filename=self.log_file,
            format='%(asctime)s::%(levelname)s::%(name)s::%(message)s',
            level=log_vals.get(self.log_level, logging.DEBUG))

    def __repr__(self):
        return '<Config({0}>'.format(', '.join('%s=%r' % (k, v)
            for (k, v) in self.__dict__.iteritems()))
