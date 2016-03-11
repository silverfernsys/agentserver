#! /usr/bin/env python

from supervisor.instanceinfo import InstanceInfo
from supervisor.procinfo import ProcInfo

class AgentInfo(object):
	def __init__(self, ip, db_name):
		self.instanceinfo = InstanceInfo(ip, db_name)

	def flush(self):
		self.instanceinfo.flush_timeseries()
