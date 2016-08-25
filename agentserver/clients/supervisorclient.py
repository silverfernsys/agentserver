#! /usr/bin/env python
import json
from supervisorclientcoordinator import scc
from constants import *
from validator import cmd_validator
from utils import get_ip
import ws


class SupervisorClient(object):
    agent_not_connected_error = json.dumps({'status': 'error', 'errors': [{'details': 'agent not connected'}]})

    def __init__(self, id, ws):
        self.id = id
        self.ip = get_ip(ws.request)
        self.ws = ws

    @classmethod
    def cmd_success_message(cls, cmd):
        return json.dumps({'status': 'success', 'details': 'command {cmd} accepted'.format(cmd=cmd)})

    @classmethod
    def unknown_cmd_error(cls, cmd):
        return json.dumps({'status': 'error', 'details': 'unknown command', 'arg': cmd})

    def error_message(self, errors):
        errors = [{'arg': k, 'details': v} for k, v in errors.items()]
        return json.dumps({'status': 'error', 'errors': errors})

    def update(self, data):
        if cmd_validator.validate(data):
            cmd = data['cmd']
            if cmd in SUPERVISOR_COMMANDS:
                if ws.SupervisorAgentHandler.command(**data):
                    self.ws.write_message(self.cmd_success_message(cmd))
                else:
                    self.ws.write_message(self.agent_not_connected_error)
            elif cmd == SUBSCRIBE_COMMAND:
                self.ws.write_message(self.cmd_success_message(cmd))
                scc.subscribe(self, **data)
            elif cmd == UNSUBSCRIBE_COMMAND:
                self.ws.write_message(self.cmd_success_message(cmd))
                scc.unsubscribe(self, **data)
        else:
            self.ws.write_message(self.error_message(cmd_validator.errors))
