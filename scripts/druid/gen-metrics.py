#! /usr/bin/env python
from datetime import datetime
import json
import random

if __name__ == '__main__':
	random.seed()
	for i in range(5):
		data = {'agent_id': i,
			'process_name': 'process_{0}'.format(i),
			'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
			'cpu': random.uniform(0, 1),
			'mem': random.randint(1, 10000000)}
		print(json.dumps(data))
