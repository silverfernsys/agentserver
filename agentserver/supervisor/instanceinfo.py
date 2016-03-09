from procinfo import ProcInfo

class InstanceInfo(object):
    def __init__(self):
        self.processes = {}

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

    def purge(self):
        self.processes = {}