import os, subprocess, json, random, sys
from datetime import datetime, timedelta
from pydruid.client import PyDruid
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension, Filter
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from utils.iso_8601 import (validate_iso_8601_period,
    validate_iso_8601_interval, iso_8601_interval_to_datetimes,
    iso_8601_period_to_timedelta)


class KafkaAccessLayer(object): 
    def __init__(self):
        self.connection = None

    def connect(self, uri):
        try:
            self.connection = KafkaProducer(bootstrap_servers=uri,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        except NoBrokersAvailable:
            print('No Kafka broker available at {0}. Exiting.'.format(uri))
            sys.exit(1)


    def write_stats(self, id, name, stats, **kwargs):
        for stat in stats:
            msg = {'agent_id': id, 'process_name': name,
                'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                'cpu': stat[1], 'mem': stat[2]}
            self.connection.send('supervisor', msg)
        self.connection.flush()

kal = KafkaAccessLayer()


class PlyQLError(Exception):
    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg


class PlyQLConnectionError(PlyQLError):
    def __init__(self, expr, msg, uri):
        super(PlyQLConnectionError, self).__init__(expr, msg)
        self.uri = uri


class PlyQL(object):
    def __init__(self, uri):
        self.uri = uri

    def query(self, q, interval=None):
        command = ['plyql', '-h', self.uri, '-q', q, '-o', 'json']
        if interval:
            command.extend(['-i', interval])
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = process.communicate()
        if err:
            try:
                (_, _, uri) = err.split(' ')
                raise PlyQLConnectionError(err,
                    'Could not connect to Druid.', uri)
            except ValueError:
                raise PlyQLError(err, 'Error executing query.') 
        else:
            return json.loads(out)


class DruidAccessLayer(object):
    timeseries_granularities = ['none', 'second', 'minute',
        'fifteen_minute', 'thirty_minute','hour', 'day',
        'week', 'month', 'quarter', 'year']

    select_granularities = ['all', 'second', 'minute',
        'fifteen_minute', 'thirty_minute','hour', 'day',
        'week', 'month', 'quarter', 'year']

    def __init__(self):
        self.connection = None
        self.plyql = None

    def connect(self, uri):
        self.connection = PyDruid('http://{0}'.format(uri), 'druid/v2/')
        self.plyql = PlyQL(uri)
        try:
            tables = self.tables()
            if 'supervisor' not in tables:
                print('Druid not correctly configured. Missing' \
                    '"supervisor" table.')
                sys.exit(1)
        except PlyQLConnectionError as e:
            print('Error connecting to Druid at {0}. Exiting.'.format(uri))
            sys.exit(1)

    def __longmax__(self, raw_metric):
        return {"type": "longMax", "fieldName": raw_metric} 

    def __doublemax__(self, raw_metric):
        return {"type": "doubleMax", "fieldName": raw_metric}

    def __validate_granularity__(self, granularity, supported_granularities):
        if granularity in self.timeseries_granularities:
            query_granularity = granularity
        elif validate_iso_8601_period(granularity):
            query_granularity = {'type': 'period', 'period': granularity}
        else:
            raise ValueError('Unsupported granularity "{0}"'.format(granularity))
        return query_granularity

    def __validate_intervals__(self, intervals):
        if not validate_iso_8601_interval(intervals):
            raise ValueError('Unsupported interval "{0}"'.format(intervals))
        return intervals

    def tables(self):
        return self.plyql.query('SHOW TABLES')

    def processes(self, agent_id, period='P6W'):
        return self.plyql.query('SELECT process_name AS process, ' \
            'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
            'WHERE agent_id = "{0}" GROUP BY process_name;'
            .format(agent_id), period)

    def timeseries(self, agent_id, process_name, granularity='none',
            intervals='P6W', descending=False):
        query_granularity = self.__validate_granularity__(granularity,
            self.timeseries_granularities)
        intervals = self.__validate_intervals__(intervals)

        return self.connection.timeseries(
            datasource='supervisor',
            granularity=query_granularity,
            descending= descending,
            intervals=intervals,
            aggregations={'cpu': self.__doublemax__('cpu'),
                'mem': self.__longmax__('mem')},
            context={'skipEmptyBuckets': 'true'},
            filter=(Dimension('agent_id') == agent_id) &
                (Dimension('process_name') == process_name))

    def select(self, agent_id, process_name, granularity='all',
            intervals='P6W', descending=True):
        query_granularity = self.__validate_granularity__(granularity,
            self.select_granularities)
        intervals = self.__validate_intervals__(intervals)

        return self.connection.select(
            datasource='supervisor',
            granularity=query_granularity,
            intervals=intervals,
            descending= descending,
            dimensions=['process_name'],
            metrics=['cpu', 'mem'],
            filter=(Dimension('agent_id') == agent_id) &
                (Dimension('process_name') == process_name),
            paging_spec={'pagingIdentifiers': {}, "threshold":1}
        )

dral = DruidAccessLayer()
