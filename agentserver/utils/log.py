import logging
from utils.ip import get_ip

def log_kafka(id, origin, name, stats, **kwargs):
    logging.getLogger(origin).debug('Flushed {0} stats for agent.id = {1}, process = {2} to Kafka.'
        .format(len(stats), id, name))

def log_auth_error(origin, auth_token):
    if auth_token:
        logging.getLogger(origin.__class__.__name__).error('Request with invalid token "{0}" ' \
            'from {1}'.format(auth_token, get_ip(origin.request)))
    else:
        logging.getLogger(origin.__class__.__name__).error('Request with missing token ' \
            'from {0}'.format(get_ip(origin.request)))

def log_authentication_error(origin, message, username):
	logging.getLogger(origin.__class__.__name__).error('Authentication: {0} ' \
        '{1} from {2}'.format(message, username, get_ip(origin.request)))