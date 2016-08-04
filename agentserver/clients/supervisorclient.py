#! /usr/bin/env python
from time import time
from datetime import datetime
import json
from sqlalchemy.orm.exc import NoResultFound
from db import dal


class SupervisorClient(object):
    SUPERVISOR_COMMANDS = ['start', 'stop', 'restart']
    CLIENT_COMMAND = 'follow'

    def __init__(self, id, ws):
        self.id = id
        self.ip = self.get_ip(ws.request)
        self.ws = ws
        self.session = dal.Session()

    def get_ip(self, request):
        return request.headers.get("X-Real-IP") or request.remote_ip

    def update(self, message):
        try:
            data = json.loads(message)
            if 'cmd' in data:
                cmd = data['cmd']
                agent_id = data['id']
                process = data['process'].split(' ')
                if cmd in type(self).SUPERVISOR_COMMANDS:
                    self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                elif cmd == type(self).CLIENT_COMMAND:
                    self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                else:
                    self.write_message(json.dumps({'status': 'error', 'type': 'unknown command'}))
            else:
                self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except ValueError as e:
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except Exception as e:
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
