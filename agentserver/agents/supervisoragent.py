#! /usr/bin/env python
import json
from time import time
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from log import log_kafka
from db import dal, kal, AgentDetail
from clients.supervisorclientcoordinator import scc
from validator import (system_stats_validator,
    states_validator, snapshot_validator)
from utils import get_ip

SNAPSHOT = 'snapshot'
STATE = 'state'
SYSTEM = 'system'

class SupervisorAgent(object):
    invalid_json_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid json'}]})
    unknown_message_type_error = json.dumps({'status': 'error', 'errors': [{'details': 'unknown message type'}]})
    snapshot_update_success = json.dumps({'status': 'success', 'details': 'snapshot updated'})
    state_update_success = json.dumps({'status': 'success', 'details': 'state updated'})
    system_stats_update_success = json.dumps({'status': 'success', 'details': 'system stats updated'})

    def __init__(self, id, ws):
        self.id = id
        self.ip = get_ip(ws.request)
        self.ws = ws
        self.session = dal.Session()

    def command(self, cmd, process):
        # message = {'cmd': 'restart web'}
        self.ws.write_message(json.dumps({'cmd': '{0} {1}'.format(cmd, process)}))

    def error_message(self, errors):
        errors = [{'arg': k, 'details': v} for k, v in errors.items()]
        return json.dumps({'status': 'error', 'errors': errors})
    
    def snapshot_update(self, data):
        if snapshot_validator.validate(data):
            for row in data[SNAPSHOT]:
                scc.update(self.id, **row)
                kal.write_stats(self.id, **row)
                log_kafka(self.id, 'SupervisorAgent', **row)
            self.ws.write_message(self.snapshot_update_success)
        else:
            self.ws.write_message(self.error_message(snapshot_validator.errors))

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
            created = AgentDetail.update_or_create(self.id, **system_stats)
            self.ws.write_message(self.system_stats_update_success)
        else:
            self.ws.write_message(self.error_message(system_stats_validator.errors))

    def update(self, message):
        try:
            data = json.loads(message)
            if SNAPSHOT in data:
                self.snapshot_update(data)
            elif STATE in data:
                self.state_update(data)
            elif SYSTEM in data:
                self.system_stats_update(data)
            else:
                self.ws.write_message(self.unknown_message_type_error)
        except ValueError as e:
            self.ws.write_message(self.invalid_json_error)
