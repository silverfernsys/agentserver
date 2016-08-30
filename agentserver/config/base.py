from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from argparse import ArgumentParser


class ConfigError(Exception):
    def __init__(self, arg):
        self.message = 'Missing configuration argument "{0}".'.format(arg)
        self.arg = arg


class MissingSection(ConfigError):
    def __init__(self, arg):
        self.message = 'Missing section "{0}" in configuration.'.format(arg)
        self.arg = arg


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

    def config_parser(self, parser):
        raise NotImplemented('config_parser must be implemented')

    def parse_config(self, paths):
        parser = ArgumentParser()
        self.config_parser(parser)

        args = parser.parse_args()

        config_parser = SafeConfigParser()
        if args.config:
            paths = [args.config]
        else:
            paths = self.config_search_paths

        config_parser.read(paths)

        try:
            data = {p: f(getattr(args, p, None) or config_parser.get(self.config_name, p)) for (p, f) in self.possible_args}
        except NoOptionError as e:
            raise ConfigError(e.args[0])
        except NoSectionError as e:
            raise MissingSection(e.section)

        if hasattr(args, 'subparser_name'):
            data['command'] = args.subparser_name

        self.__dict__.update(data)

    def __repr__(self):
        return '<Config({0}>'.format(', '.join('%s=%r' % (k, v)
            for (k, v) in self.__dict__.iteritems()))
