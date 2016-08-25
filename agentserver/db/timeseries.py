import os, subprocess, json, random
from datetime import datetime, timedelta
from pydruid.client import PyDruid
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension, Filter
from kafka import KafkaProducer
from utils.iso_8601 import (validate_iso_8601_period,
    validate_iso_8601_interval, iso_8601_interval_to_datetimes,
    iso_8601_period_to_timedelta)


class KafkaProducerMock(object):
    def __init__(self, bootstrap_servers=None, value_serializer=None):
        pass
    def send(self, topic, data):
        pass
    def flush(self):
        pass


class KafkaAccessLayer(object): 
    def __init__(self):
        self.connection = None

    def connect(self, uri):
        if uri.lower() == 'debug':
            self.connection = KafkaProducerMock()
        else:
            self.connection = KafkaProducer(bootstrap_servers=uri,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    def write_stats(self, id, name, stats, **kwargs):
        for stat in stats:
            msg = {'agent_id': id, 'process_name': name,
                'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                'cpu': stat[1], 'mem': stat[2]}
            self.connection.send('supervisor', msg)
        self.connection.flush()

kal = KafkaAccessLayer()


class PyDruidResultMock(object):
    def __init__(self, result):
        self.result = result


class PyDruidMock(object):
    def groupby(self, datasource, granularity, intervals, dimensions,
        filter, aggregations):
        f = Filter.build_filter(filter)
        if f['type'] == 'selector' and f['dimension'] == 'agent_id' and 'value' in f:
            try:
                body = open(os.path.join(self.fixtures_dir,
                    'groupby{0}.json'.format(f['value']))).read().decode('utf-8')
            except:
                body = '[]'
        else:
            body = '[]'
        return PyDruidResultMock(body)

    def __granularity_to_timedelta__(self, granularity):
        if granularity == 'none' or granularity == 'second':
            return timedelta(seconds=1)
        elif granularity == 'minute':
            return timedelta(minutes=1)
        elif granularity == 'fifteen_minute':
            return timedelta(minutes=15)
        elif granularity == 'thirty_minute':
            return timedelta(minutes=30)
        elif granularity == 'hour':
            return timedelta(hours=1)
        elif granularity == 'day':
            return timedelta(days=1)
        elif granularity == 'week':
            return timedelta(weeks=1)
        elif granularity == 'month':
            return timedelta(days=30)
        elif granularity == 'quarter':
            return timedelta(days=30 * 4)
        elif granularity == 'year':
            return timedelta(days=365)
        else:
            return timedelta(hours=1)

    def timeseries(self, datasource, granularity, descending, intervals,
        aggregations, context, filter):
        f = Filter.build_filter(filter)
        if f['type'] == 'and' and f['fields'][0]['type'] == 'selector' and \
            f['fields'][0]['dimension'] == 'agent_id' and \
            f['fields'][1]['type'] == 'selector' and \
            f['fields'][1]['dimension'] == 'process_name':
            agent_id = f['fields'][0]['value']
            process_name = f['fields'][1]['value']

            (interval_start, interval_end) = iso_8601_interval_to_datetimes(intervals)
            if interval_end is None:
                interval_end = datetime.now()

            if granularity in DruidAccessLayer.timeseries_granularities:
                query_granularity = self.__granularity_to_timedelta__(granularity)
            else:
                query_granularity = iso_8601_period_to_timedelta(granularity['period'])

            body = []
            curr_time = interval_start

            while curr_time < interval_end:
                body.append({'timestamp': curr_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    'result': {'cpu': random.uniform(0, 1),
                    'mem': random.randint(1, 10000000)}})
                curr_time += query_granularity
        else:
            body = []
        return PyDruidResultMock(body)

    def select(self, datasource, granularity, intervals, descending,
        dimensions, metrics, filter, paging_spec):
        f = Filter.build_filter(filter)
        print('f: %s' % f)
        body = []
        return PyDruidResultMock(body)


class DruidAccessLayer(object):
    timeseries_granularities = ['none', 'second', 'minute',
        'fifteen_minute', 'thirty_minute','hour', 'day',
        'week', 'month', 'quarter', 'year']

    select_granularities = ['all', 'second', 'minute',
        'fifteen_minute', 'thirty_minute','hour', 'day',
        'week', 'month', 'quarter', 'year']

    def __init__(self):
        self.connection = None

    def connect(self, uri):
        if uri.lower() == 'debug':
            self.connection = PyDruidMock()
        else:
            self.connection = PyDruid('http://{0}'.format(uri), 'druid/v2/')

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


class PlyQLAccessLayer(object):
    def __init__(self):
        self.uri = None

    def connect(self, uri):
        if uri.lower() == 'debug':
            self.uri = 'debug'
        else:
            self.uri = uri

    def query(self, q, interval=None):
        if not self.uri:
            raise UnboundLocalError('Please connect to valid uri before calling query.')

        command = ['plyql', '-h', self.uri, '-q', q, '-o', 'json']
        if interval:
            command.extend(['-i', interval])
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = process.communicate()
        if err:
            return json.dumps({'error': err.strip()})
        else:
            return out

    def processes(self, agent_id, period='P6W'):
        return self.query('SELECT process_name AS process, ' \
            'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
            'WHERE agent_id = "{0}" GROUP BY process_name;'
            .format(agent_id), period)

pal = PlyQLAccessLayer()