from tornado.escape import json_encode
from agentserver.db.models import AgentDetail
from agentserver.db.timeseries import kafka
from agentserver.clients.supervisorclientcoordinator import scc
from agentserver.utils.validators import (system_stats_validator,
                              states_validator, snapshot_validator)
from agentserver.utils.ip import get_ip
from agentserver.utils.log import log_kafka


SNAPSHOT = 'snapshot'
STATE = 'state'
SYSTEM = 'system'


class SupervisorAgent(object):
    unknown_message_type_error = json_encode(
        {'status': 'error', 'errors': [{'details': 'unknown message type'}]})
    snapshot_update_success = json_encode(
        {'status': 'success', 'details': 'snapshot updated'})
    state_update_success = json_encode(
        {'status': 'success', 'details': 'state updated'})
    system_stats_update_success = json_encode(
        {'status': 'success', 'details': 'system stats updated'})

    def __init__(self, id, ws):
        self.id = id
        self.ip = get_ip(ws.request)
        self.ws = ws

    def command(self, cmd, process):
        # message = {'cmd': 'restart web'}
        self.ws.write_message(json_encode(
            {'cmd': '{0} {1}'.format(cmd, process)}))

    def error_message(self, errors):
        errors = [{'arg': k, 'details': v} for k, v in errors.items()]
        return json_encode({'status': 'error', 'errors': errors})

    def snapshot_update(self, data):
        if snapshot_validator.validate(data):
            for row in data[SNAPSHOT]:
                scc.update(self.id, **row)
                kafka.write_stats(self.id, **row)
                log_kafka(self.id, 'SupervisorAgent', **row)
            self.ws.write_message(self.snapshot_update_success)
        else:
            print(snapshot_validator.errors)
            self.ws.write_message(
                self.error_message(snapshot_validator.errors))

    def state_update(self, data):
        update = data[STATE]
        if states_validator.validate(update):
            scc.update(self.id, **update)
            self.ws.write_message(self.state_update_success)
        else:
            self.ws.write_message(self.error_message(states_validator.errors))

    def system_stats_update(self, data):
        system_stats = data[SYSTEM]
        if system_stats_validator.validate(system_stats):
            AgentDetail.update_or_create(self.id, **system_stats)
            self.ws.write_message(self.system_stats_update_success)
        else:
            self.ws.write_message(self.error_message(
                system_stats_validator.errors))

    def update(self, data):
        if SNAPSHOT in data:
            self.snapshot_update(data)
        elif STATE in data:
            self.state_update(data)
        elif SYSTEM in data:
            self.system_stats_update(data)
        else:
            self.ws.write_message(self.unknown_message_type_error)
