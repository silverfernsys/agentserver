#! /usr/bin/env python
from datetime import datetime
import json
import random
from kafka import KafkaProducer

if __name__ == '__main__':
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    random.seed()
    for i in range(5):
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        data = {'agent_id': 1,
                'process_name': 'process_{0}'.format(i),
                'timestamp': timestamp,
                'cpu': random.uniform(0, 1),
                'mem': random.randint(1, 10000000)}
        producer.send('supervisor', data)
        producer.flush()
