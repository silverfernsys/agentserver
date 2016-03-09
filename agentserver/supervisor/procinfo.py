#!/usr/bin/env python
from time import time

STATE_MAP = {
    'STOPPED': 0,
    'STARTING': 10,
    'RUNNING': 20,
    'BACKOFF': 30,
    'STOPPING': 40,
    'EXITED': 100,
    'FATAL': 200,
    'UNKNOWN': 1000 
}

class ProcInfo(object):
    def __init__(self, name, group, pid, state, statename, start):
        self.name = name
        self.group = group
        self.pid = pid
        self._state = state
        self._statename = statename
        self.start = start
        self.cpu = []
        self.mem = []

    @property
    def state(self):
        return self._state

    @property
    def statename(self):
        return self._statename
    
    @statename.setter
    def statename(self, val):
        try:
            self._statename = val
            self._state = STATE_MAP[val]
        except Exception as e:
            print(e)

    def update(self, data):
        self.cpu.extend(data['cpu'])
        self.mem.extend(data['mem'])
    
    def _binary_search_helper(self, array, value, start, end):
        if (start >= end):
            return end
        else:
            mid = start + (end - start) / 2
            if array[mid][0] > value:
                return self._binary_search_helper(array, value, start, mid)
            else:
                return self._binary_search_helper(array, value, mid + 1, end)

    def _binary_search(self, array, value):
        index = self._binary_search_helper(array, value, 0, len(array))
        return array[index:len(array)]

    def get_cpu(self, time=None):
        if time is None:
            return self.cpu
        else:
            return self._binary_search(self.cpu, time)

    def get_mem(self, time=None):
        if time is None:
            return self.mem
        else:
            return self._binary_search(self.mem, time)

    def __str__(self):
        return 'name: %s, group: %s, pid: %s, cpu: %s, mem: %s' % (self.name, self.group, self._pid, self.cpu, self.mem)

    def to_dict(self):
        return {'name': self.name,
        'group': self.group,
        'pid': self._pid,
        'state': self._state,
        'statename': self._statename,
        'start': self.start,
        'cpu': self.cpu,
        'mem': self.mem,
        }


    def data(self):
        return {'name': self.name,
        'group': self.group,
        'pid': self._pid,
        'state': self._state,
        'statename': self._statename,
        'start': self.start,
        'cpu': self.cpu,
        'mem': self.mem,
        }

    def reset(self):
        self.cpu = []
        self.mem = []
