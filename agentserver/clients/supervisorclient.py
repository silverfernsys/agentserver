#! /usr/bin/env python
from time import time
from datetime import datetime
import json
from db import dral
from supervisorclientcoordinator import scc
from constants import *
from validator import cmd_validator
import ws


class SupervisorClient(object):
    def __init__(self, id, ws):
        self.id = id
        self.ip = self.get_ip(ws.request)
        self.ws = ws

    def get_ip(self, request):
        return request.headers.get("X-Real-IP") or request.remote_ip

    def update(self, message):
        try:
            data = json.loads(message)
            if cmd_validator.validate(data):
                cmd = data['cmd']
                if cmd in SUPERVISOR_COMMANDS:
                    if ws.SupervisorAgentHandler.command(**data):
                        self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                    else:
                        self.ws.write_message(json.dumps({'status': 'error', 'type': 'agent not connected'}))
                elif cmd == SUBSCRIBE_COMMAND:
                    self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                    scc.subscribe(self, **data)
                elif cmd == UNSUBSCRIBE_COMMAND:
                    self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                    scc.unsubscribe(self, **data)
                else:
                    self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown command'}))
            else:
                self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except ValueError as e:
            print('ValueError: %s' % e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except Exception as e:
            print('***Exception: %s***' % e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
