#! /usr/bin/env python
from procinfo import ProcInfo
from influxdb import InfluxDBClient
from config import config

class InstanceInfo(object):
    def __init__(self, ip):
        self.processes = {}
        self.agent_ip = ip
        (username, password, host, port) = self._parseTimeseriesURI(config.data['timeseries'])
        dbname = '%s-supervisor' % self.agent_ip
        self.client = InfluxDBClient(host, port, user, password, dbname)

    def get(self, group, name):
        try:
            return self.processes[group][name]
        except:
            None

    def add(self, proc):
        if proc.group not in self.processes:
            self.processes[proc.group] = {}
        self.processes[proc.group][proc.name] = proc

    # A class method generator that yields the contents of the 'processes' dictionary
    def all(self):
        for group in self.processes:
            for name in self.processes[group]:
                yield self.processes[group][name]
        raise StopIteration()

    def update(self, data):
        for d in data:
            info = self.get(d['group'], d['name'])
            if info:
                info.update(d)
            else:
                # name, group, pid, state, statename, start
                info = ProcInfo(d['name'], d['group'], d['pid'],
                    d['state'], d['statename'], d['start'])
                info.update(d)
                self.add(info)

    def data(self):
        data = []
        for p in self.all():
            data.append(p.data())
        return data

    def reset(self):
        for p in self.all():
            p.reset()

    def flush_timeseries():
        pass

    def purge(self):
        self.processes = {}

    def _parseTimeseriesURI(self, uri):
        split_uri = uri.split('://')
        if split_uri[0] == 'influxdb':
            up_hp = split_uri[1].split('@')
            username = up_hp[0].split(':')[0]
            password = up_hp[0].split(':')[1]
            host = up_hp[1].split(':')[0]
            port = up_hp[1].split(':')[1]
            return (username, password, host, port)
        else:
            return (None, None, None, None)

