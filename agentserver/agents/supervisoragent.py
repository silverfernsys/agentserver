#! /usr/bin/env python
from time import time
from datetime import datetime
import json
from sqlalchemy.orm.exc import NoResultFound
from db import dal, kal, ProcessDetail, ProcessState
from clients.supervisorclientcoordinator import scc


class ProcessInfo(object):
    def __init__(self, id, name, start, state):
        self.id = id
        self.name = name
        self.start = start
        self.state = state


class SupervisorAgent(object):
    def __init__(self, id, ws):
        self.id = id
        self.ip = self.get_ip(ws.request)
        self.ws = ws
        self.session = dal.Session()
        self.processes = {}

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
                    if name in self.processes:
                        process = self.processes['name']
                        if process.start != start:
                            process.start = start
                            ProcessDetail.update_or_create(name, self.id, start, self.session)
                    else:
                        detail = ProcessDetail.update_or_create(name, self.id, start, self.session)
                        state = ProcessState(detail_id=detail.id, name=row['statename'])
                        self.session.add(state)
                        self.session.commit()
                        process = ProcessInfo(detail.id, name, start, row['statename'])
                        self.processes['name'] = process
                    for stat in row['stats']:
                        msg = {'agent_id': self.id, 'process_id': process.id,
                            'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            'cpu': stat[1], 'mem': stat[2]}
                        kal.connection.send('supervisor', msg)
                    scc.agents[self.id].processes[name].update(start,
                        row['statename'],
                        datetime.utcfromtimestamp(row['stats'][-1][0]))
                kal.connection.flush()
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'snapshot updated'}))
            elif 'state_update' in data:
                update = data['state_update']
                name = update['name']
                state = update['statename']
                start = datetime.utcfromtimestamp(update['start'])
                if update['name'] in self.processes:
                    process = self.processes[name]
                    process.state = state
                    process.start = start
                    ProcessDetail.update_or_create(name, self.id, start, self.session)
                else:
                    detail = ProcessDetail.update_or_create(name, self.id, start, self.session)
                    process = ProcessInfo(detail.id, name, start, state)
                    state = ProcessState(detail_id=detail.id, name=state)
                    self.session.add(state)
                    self.session.commit()
                scc.agents[self.id].processes[name].update(start, state, None)
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'state updated'}))
            else:
                self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except ValueError as e:
            # print(e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except Exception as e:
            # print(e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))

    # def add(self, proc):
    #     if proc.group not in self.processes:
    #         self.processes[proc.group] = {}
    #     self.processes[proc.group][proc.name] = proc

    # # A class method generator that yields the contents of the 'processes' dictionary
    # def all(self):
    #     for group in self.processes:
    #         for name in self.processes[group]:
    #             yield self.processes[group][name]
    #     raise StopIteration()
