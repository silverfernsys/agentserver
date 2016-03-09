#! /usr/bin/env python

from supervisor.instanceinfo import InstanceInfo
from supervisor.procinfo import ProcInfo

class AgentInfo(object):
	def __init__(self, ip):
		self.instanceinfo = InstanceInfo(ip)
