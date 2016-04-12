from __future__ import division
import binascii
import os
from datetime import datetime, timedelta
import re


def uuid():
    return binascii.hexlify(os.urandom(20)).decode()

def timestamp(dt, epoch=datetime(1970,1,1)):
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 86400) * 10**6) / 10**6

def is_rfc_3339_format(date_str):
	prog = re.compile("^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[A-Z]?$")
	result = prog.match(date_str)
	print('result: %s' % result)
	if result:
		return True
	else:
		return False
