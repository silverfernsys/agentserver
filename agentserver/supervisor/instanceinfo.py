#! /usr/bin/env python
from procinfo import ProcInfo
from influxdb import InfluxDBClient, SeriesHelper
from config import config
from time import time
from db import tal

class InstanceInfo(object):
    def __init__(self, ip, dbname):
        self.processes = {}
        self.agent_ip = ip
        self.dbname = dbname
        tal.connect(config.data['timeseries'], self.dbname)
        # (username, password, host, port) = self._parseTimeseriesURI(config.data['timeseries'])
        # self.client = InfluxDBClient(host, port, username, password, dbname)
        self.time = 0.0

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

    def flush_timeseries(self):
        print('flush_timeseries')
        """
        This will flush timeseries data for this instance.
        Flushes all data newer than self.time. Otherwise,
        breaks from loop.
        """
        class SupervisorSeriesHelper(SeriesHelper):
            # Meta class stores time series helper configuration.
            class Meta:
                # The client should be an instance of InfluxDBClient.
                client = tal.connection(self.dbname)
                # The series name must be a string. Add dependent fields/tags in curly brackets.
                series_name = 'supervisor'
                # Defines all the fields in this time series.
                fields = ['cpu', 'mem', 'time']
                # Defines all the tags for the series.
                tags = ['processgroup', 'processname']
                # Defines the number of data points to store prior to writing on the wire.
                bulk_size = 5
                # autocommit must be set to True when using bulk_size
                autocommit = True

        max_timestamp = 0.0
        for process in self.all():
            if len(process.cpu) == len(process.mem):
                max_timestamp = max(max_timestamp, process.cpu[len(process.cpu) - 1][0])
                # Work backwards through the array, breaking as soon as
                # a timestamp older than self.time is reached.
                length = len(process.cpu)
                for i in range(len(process.cpu)):
                    cpu = process.cpu[length - i - 1][1]
                    mem = process.mem[length - i - 1][1]
                    timestamp = process.cpu[length - i - 1][0]
                    if timestamp < self.time:
                        break
                    else:
                        SupervisorSeriesHelper(processgroup=process.group,
                            processname=process.name, cpu=cpu, mem=mem, time=timestamp)
            else:
                print('ERROR with cpu and mem stats')
        self.time = max_timestamp
        SupervisorSeriesHelper.commit()
        print(SupervisorSeriesHelper._json_body_())


    def purge(self):
        """
        This purges all processes
        """
        self.processes = {}
