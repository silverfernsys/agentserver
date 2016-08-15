#! /usr/bin/env python
from time import time
from datetime import datetime
import json
from db import dral
from supervisorclientcoordinator import scc
import ws

class SupervisorClient(object):
    SUPERVISOR_COMMANDS = ['start', 'stop', 'restart']
    SUBSCRIBE_COMMAND = 'sub'
    UNSUBSCRIBE_COMMAND = 'unsub'

    def __init__(self, id, ws):
        self.id = id
        self.ip = self.get_ip(ws.request)
        self.ws = ws

    def get_ip(self, request):
        return request.headers.get("X-Real-IP") or request.remote_ip

    def update(self, message):
        try:
            data = json.loads(message)
            if 'cmd' in data:
                cmd = data['cmd']
                agent_id = data['id']
                process = data['process'] #.split(' ')
                if cmd in type(self).SUPERVISOR_COMMANDS:
                    try:
                        agent = ws.SupervisorAgentHandler.IDs[agent_id]
                        # message = {'cmd': 'restart web'}
                        agent.command(json.dumps({'cmd': '{0} {1}'.format(cmd, process)}))
                        self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                    except Exception as e:
                        self.ws.write_message(json.dumps({'status': 'error', 'type': 'agent not connected'}))
                elif cmd == type(self).SUBSCRIBE_COMMAND:
                    scc.subscribe(self, agent_id, process)
                    self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                elif cmd == type(self).UNSUBSCRIBE_COMMAND:
                    scc.unsubscribe(self, agent_id, process)
                    self.ws.write_message(json.dumps({'status': 'success', 'type': 'command {cmd} accepted'.format(cmd=cmd)}))
                else:
                    self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown command'}))
            else:
                self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except ValueError as e:
            print('ValueError: %s' % e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except Exception as e:
            print('Exception: %s' % e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
