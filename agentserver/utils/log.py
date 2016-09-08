import logging
from ip import get_ip


log_vals = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET}


class LoggingError(Exception):

    def __init__(self, arg):
        self.message = 'LoggingError: {0}'.format(arg)
        self.arg = arg


class LogFileError(LoggingError):

    def __init__(self, arg):
        self.message = 'Error opening log file "{0}".'.format(arg)
        self.arg = arg


def config_logging(config):
    try:
        filename = config.arguments.agentserver.log_file
        format = '%(asctime)s::%(levelname)s::%(name)s::%(message)s'
        level = log_vals.get(config.arguments.agentserver.log_level, logging.DEBUG)
        logging.basicConfig(filename=filename,
                            format=format,
                            level=level)
    except IOError:
        raise LogFileError(config.log_file)


def log_kafka(id, origin, name, stats, **kwargs):
    logging.getLogger(origin).debug('Flushed {0} stats for agent.id = {1}, '
                                    'process = {2} to Kafka.'
                                    .format(len(stats), id, name))


def log_auth_error(origin, auth_token):
    if auth_token:
        logging.getLogger(origin.__class__.__name__).error(
            'Request with invalid token "{0}" '
            'from agentserver.{1}'.format(auth_token, get_ip(origin.request)))
    else:
        logging.getLogger(origin.__class__.__name__).error(
            'Request with missing token '
            'from agentserver.{0}'.format(get_ip(origin.request)))


def log_authentication_error(origin, message, username):
    logging.getLogger(origin.__class__.__name__).error(
        'Authentication: {0} {1} from agentserver.{2}'
        .format(message, username, get_ip(origin.request)))
