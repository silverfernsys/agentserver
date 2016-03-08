import binascii
import os

def resolveConfig(config, args):
    """
    Returns a dictionary consisting of keys found
    in config and the values of config overwritten
    by values of args
    """
    data = {}
    try:
        data['log_level'] = args.log_level or config.get('agentserver', 'log_level')
    except:
        data['log_level'] = config.get('agentserver', 'log_level')

    try:
        data['log_file'] = args.log_file or config.get('agentserver', 'log_file')
    except:
        data['log_file'] = config.get('agentserver', 'log_file')

    try:
        data['database'] = args.database or config.get('agentserver', 'database')
    except:
        data['database'] = config.get('agentserver', 'database')

    try:
        data['port'] = args.port or config.getint('agentserver', 'port')
    except:
        data['port'] = config.getint('agentserver', 'port')

    try:
        data['max_wait_seconds_before_shutdown'] = args.max_wait_seconds_before_shutdown or config.getint('agentserver', 'max_wait_seconds_before_shutdown')
    except:
        data['max_wait_seconds_before_shutdown'] = config.getint('agentserver', 'max_wait_seconds_before_shutdown')
    return data


def uuid():
    return binascii.hexlify(os.urandom(20)).decode()