#! /usr/bin/env python
from datetime import datetime, timedelta
from agentserver.db import pal
import json

if __name__ == '__main__':
	pal.connect('localhost:8082')

	# from_time = (datetime.utcnow() - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
	# to_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
	# result = pal.query('SELECT process_name AS process, ' \
	# 	'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
	# 	'WHERE "{0}" <= __time AND __time < ' \
	# 	'"{1}" AND agent_id = "1" GROUP BY ' \
	# 	'process_name;'.format(from_time, to_time))
	# print(result)

	result = pal.query('SELECT process_name AS process, ' \
        'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
        'WHERE agent_id = "1" GROUP BY process_name;', 'P6W')
	print(result)



