#! /usr/bin/env python
import json, logging
from time import time
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from db import dal, kal, AgentDetail
from clients.supervisorclientcoordinator import scc


class SupervisorAgent(object):
    def __init__(self, id, ws):
        self.id = id
        self.ip = self.get_ip(ws.request)
        self.ws = ws
        self.session = dal.Session()
        self.logger = logging.getLogger('SupervisorAgent')

    def get_ip(self, request):
        return request.headers.get("X-Real-IP") or request.remote_ip

    def command(self, message):
        self.ws.write_message(message)

    def update(self, message):
        try:
            data = json.loads(message)
            if 'snapshot_update' in data:
                update = data['snapshot_update']
                for row in update:
                    name = row['name']
                    start = datetime.utcfromtimestamp(row['start'])
                    state = row['statename']
                    if len(row['stats']) > 0:
                        updated = datetime.utcfromtimestamp(row['stats'][-1][0])
                    else:
                        updated = datetime.utcnow()
                    scc.update(self.id, name, start, row['statename'], updated)
                    for stat in row['stats']:
                        msg = {'agent_id': self.id, 'process_name': name,
                            'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            'cpu': stat[1], 'mem': stat[2]}
                        kal.connection.send('supervisor', msg)
                    self.logger.debug('Flushed %d stats for agent.id = %d, process = %s to Kafka.'
                        % (len(row['stats']), self.id, name))
                kal.connection.flush()
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'snapshot updated'}))
            elif 'state_update' in data:
                update = data['state_update']
                name = update['name']
                state = update['statename']
                start = datetime.utcfromtimestamp(update['start'])
                scc.update(self.id, name, start, update['statename'], datetime.utcnow())
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'state updated'}))
            elif 'system_stats' in data:
                system_stats = data['system_stats']
                created = AgentDetail.update_or_create(self.id, **system_stats)
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'system stats updated'}))
            else:
                self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except ValueError as e:
            # print('**ValueError: %s' % e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except Exception as e:
            # print('**Exception: %s, type: %s, dir: %s' % (e, type(e), dir(e)))
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
