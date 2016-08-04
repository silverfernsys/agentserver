#! /usr/bin/env python
from time import time
from datetime import datetime
import json
from sqlalchemy.orm.exc import NoResultFound
from db import dal, kal, ProcessDetail, ProcessState


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

    def update(self, message):
        try:
            data = json.loads(message)
            if 'snapshot_update' in data:
                update = data['snapshot_update']
                for row in update:
                    name = row['name']
                    start = datetime.fromtimestamp(row['start'])
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
                            'timestamp': datetime.fromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            'cpu': stat[1], 'mem': stat[2]}
                        kal.connection.send('supervisor', msg)
                kal.connection.flush()
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'snapshot updated'}))
            elif 'state_update' in data:
                update = data['state_update']
                name = update['name']
                state = update['statename']
                start = datetime.fromtimestamp(update['start'])
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
                # print(update)
                self.ws.write_message(json.dumps({'status': 'success', 'type': 'state updated'}))
            else:
                self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except ValueError as e:
            # print(e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))
        except Exception as e:
            # print(e)
            self.ws.write_message(json.dumps({'status': 'error', 'type': 'unknown message type'}))

    # def __init__(self, ip, dbname, conn):
    #     self.processes = {}
    #     self.agent_ip = ip
    #     self.dbname = dbname
    #     self.conn = conn
    #     # tal.connect(config.data['timeseries'], self.dbname)
    #     # (username, password, host, port) = self._parseTimeseriesURI(config.data['timeseries'])
    #     # self.client = InfluxDBClient(host, port, username, password, dbname)
    #     self.time = 0.0

    # def get(self, group, name):
    #     try:
    #         return self.processes[group][name]
    #     except:
    #         None

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

    # def snapshot_update(self, data):
    #     for d in data:
    #         info = self.get(d['group'], d['name'])
    #         if info:
    #             info.update(d)
    #         else:
    #             # name, group, pid, state, statename, start
    #             info = ProcInfo(d['name'], d['group'], d['pid'],
    #                 d['state'], d['statename'], d['start'])
    #             info.update(d)
    #             self.add(info)

    # def state_update(self, data):
    #     info = self.get(data['group'], data['name'])
    #     if info != None:
    #         info.update_state(data)

    # def data(self):
    #     data = []
    #     for p in self.all():
    #         data.append(p.data())
    #     return data

    # def snapshot(self):
    #     return [p.snapshot() for p in self.all()]

    # def reset(self):
    #     for p in self.all():
    #         p.reset()

    # def flush_timeseries(self):
    #     print('flush_timeseries')
    #     for process in self.all():
    #         data = json.dumps(process.data())




            # kal.connection.send('supervisor', data.encode('utf-8'))
        # https://github.com/dpkp/kafka-python
        # kal.connection.send('supervisor', b'some message')

    # def flush_timeseries(self):
    #     print('flush_timeseries')
    #     """
    #     This will flush timeseries data for this instance.
    #     Flushes all data newer than self.time. Otherwise,
    #     breaks from loop.
    #     """
    #     class SupervisorSeriesHelper(SeriesHelper):
    #         # Meta class stores time series helper configuration.
    #         class Meta:
    #             # The client should be an instance of InfluxDBClient.
    #             client = tal.connection(self.dbname)
    #             # The series name must be a string. Add dependent fields/tags in curly brackets.
    #             series_name = 'supervisor'
    #             # Defines all the fields in this time series.
    #             fields = ['cpu', 'mem', 'time']
    #             # Defines all the tags for the series.
    #             tags = ['processgroup', 'processname']
    #             # Defines the number of data points to store prior to writing on the wire.
    #             bulk_size = 5
    #             # autocommit must be set to True when using bulk_size
    #             autocommit = True

    #     max_timestamp = 0.0
    #     for process in self.all():
    #         if len(process.cpu) == len(process.mem):
    #             max_timestamp = max(max_timestamp, process.cpu[len(process.cpu) - 1][0])
    #             # Work backwards through the array, breaking as soon as
    #             # a timestamp older than self.time is reached.
    #             length = len(process.cpu)
    #             for i in range(len(process.cpu)):
    #                 cpu = process.cpu[length - i - 1][1]
    #                 mem = process.mem[length - i - 1][1]
    #                 timestamp = process.cpu[length - i - 1][0]
    #                 if timestamp < self.time:
    #                     break
    #                 else:
    #                     SupervisorSeriesHelper(processgroup=process.group,
    #                         processname=process.name, cpu=cpu, mem=mem, time=timestamp)
    #         else:
    #             print('ERROR with cpu and mem stats')
    #     self.time = max_timestamp
    #     SupervisorSeriesHelper.commit()
    #     print(SupervisorSeriesHelper._json_body_())


    # def purge(self):
    #     """
    #     This purges all processes
    #     """
    #     self.processes = {}
# class ProcInfo(object):
#     def __init__(self, name, group, pid, state, statename, start):
#         self.name = name
#         self.group = group
#         self.pid = pid
#         self._state = state
#         self._statename = statename
#         self.start = start
#         self.cpu = []
#         self.mem = []

#     @property
#     def state(self):
#         return self._state

#     @property
#     def statename(self):
#         return self._statename
    
#     @statename.setter
#     def statename(self, val):
#         try:
#             self._statename = val
#             self._state = STATE_MAP[val]
#         except Exception as e:
#             print(e)

#     def update(self, data):
#         self.cpu.extend(data['cpu'])
#         self.mem.extend(data['mem'])

#     def update_state(self, data):
#         self.statename = data['statename']
#         self.start = data['start']

#     def _binary_search_helper(self, array, value, start, end):
#         if (start >= end):
#             return end
#         else:
#             mid = start + (end - start) / 2
#             if array[mid][0] > value:
#                 return self._binary_search_helper(array, value, start, mid)
#             else:
#                 return self._binary_search_helper(array, value, mid + 1, end)

#     def _binary_search(self, array, value):
#         index = self._binary_search_helper(array, value, 0, len(array))
#         return array[index:len(array)]

#     def get_cpu(self, time=None):
#         if time is None:
#             return self.cpu
#         else:
#             return self._binary_search(self.cpu, time)

#     def get_mem(self, time=None):
#         if time is None:
#             return self.mem
#         else:
#             return self._binary_search(self.mem, time)

#     def __str__(self):
#         return 'name: %s, group: %s, pid: %s, cpu: %s, mem: %s' % (self.name, self.group, self.pid, self.cpu, self.mem)

#     def to_dict(self):
#         return {'name': self.name,
#         'group': self.group,
#         'pid': self.pid,
#         'state': self._state,
#         'statename': self._statename,
#         'start': self.start,
#         'cpu': self.cpu,
#         'mem': self.mem,
#         }


#     def data(self):
#         return {'name': self.name,
#         'group': self.group,
#         'pid': self.pid,
#         'state': self._state,
#         'statename': self._statename,
#         'start': self.start,
#         'cpu': self.cpu,
#         'mem': self.mem,
#         }

#     def snapshot(self):
#         return {'name': self.name,
#         'group': self.group,
#         'pid': self.pid,
#         'state': self._state,
#         'statename': self._statename,
#         'start': self.start,
#         'cpu': self.cpu[-1],
#         'mem': self.mem[-1],
#         }

#     def reset(self):
#         self.cpu = []
#         self.mem = []

