from datetime import datetime
from cerberus import Validator
from agentserver.clients.constants import (SUPERVISOR_COMMANDS,
                               SUBSCRIBE_COMMAND, UNSUBSCRIBE_COMMAND)


system_stats_schema = {
    'dist_name': {'type': 'string', 'required': True},
    'dist_version': {'type': 'string', 'required': True},
    'hostname': {'type': 'string', 'required': True},
    'num_cores': {'type': 'integer', 'required': True},
    'memory': {'type': 'integer', 'required': True},
    'processor': {'type': 'string', 'required': True}
}

system_stats_validator = Validator(system_stats_schema)


states_schema = {
    'group': {'type': 'string', 'required': True},
    'name': {'type': 'string', 'required': True},
    'statename': {'type': 'string', 'required': True,
                  'allowed': ['STOPPED', 'STARTING', 'RUNNING',
                              'BACKOFF', 'STOPPING', 'EXITED',
                              'FATAL', 'UNKNOWN']},
    'pid': {'type': 'integer', 'required': True, 'nullable': True},
    'start': {'type': 'integer', 'required': True},
    'state': {'type': 'integer', 'required': True,
              'allowed': [0, 10, 20, 30, 40, 100, 200, 1000]}
}

states_validator = Validator(states_schema)


snapshot_schema = {
    'snapshot': {'type': 'list', 'required': True,
                 'items': {
                         'group': {'type': 'string', 'required': True},
                         'name': {'type': 'string', 'required': True},
                     'statename': {'type': 'string', 'required': True,
                                   'allowed': ['STOPPED', 'STARTING',
                                               'RUNNING', 'BACKOFF',
                                               'STOPPING', 'EXITED',
                                               'FATAL', 'UNKNOWN']},
                     'pid': {'type': 'integer', 'required': True,
                             'nullable': True},
                     'start': {'type': 'integer', 'required': True},
                     'state': {'type': 'integer', 'required': True,
                               'allowed': [0, 10, 20, 30, 40, 100, 200, 1000]},
                     'stats': {'type': 'list', 'required': True,
                               'schema': {'type': 'list', 'items':
                                          [{'type': 'float'},
                                           {'type': 'float'},
                                           {'type': 'integer'}]}}
                 }
                 }
}

snapshot_validator = Validator(snapshot_schema)


cmd_schema = {
    'cmd': {'type': 'string', 'required': True,
            'allowed': SUPERVISOR_COMMANDS + [SUBSCRIBE_COMMAND] +
            [UNSUBSCRIBE_COMMAND]},
    'id': {'type': 'integer', 'required': True},
    'process': {'type': 'string', 'required': True}
}

cmd_validator = Validator(cmd_schema)

def timestamp(timestamp_str):
    try:
        datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        return True
    except:
        return False
