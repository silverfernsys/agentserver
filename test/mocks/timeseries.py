import os
import json
import random
import re
from datetime import datetime, timedelta
from pydruid.utils.filters import Filter
from db.timeseries import DruidAccessLayer
from utils.iso_8601 import (iso_8601_interval_to_datetimes,
                            iso_8601_period_to_timedelta)


resources = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'resources'))


class KafkaProducerMock(object):

    def __init__(self, bootstrap_servers=None, value_serializer=None):
        pass

    def send(self, topic, data):
        pass

    def flush(self):
        pass


class PyDruidResultMock(object):

    def __init__(self, result):
        self.result = result


class PyDruidMock(object):

    def groupby(self, datasource, granularity, intervals, dimensions,
                filter, aggregations):
        f = Filter.build_filter(filter)
        if f['type'] == 'selector' and \
           f['dimension'] == 'agent_id' and 'value' in f:
            try:
                filename = 'groupby{0}.json'.format(f['value'])
                filepath = os.path.join(resources, filename)
                body = open(filepath).read().decode('utf-8')
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
            # agent_id = f['fields'][0]['value']
            # process_name = f['fields'][1]['value']

            (interval_start, interval_end) = \
                iso_8601_interval_to_datetimes(intervals)
            if interval_end is None:
                interval_end = datetime.now()

            if granularity in DruidAccessLayer.timeseries_granularities:
                query_granularity = self.__granularity_to_timedelta__(
                    granularity)
            else:
                query_granularity = iso_8601_period_to_timedelta(granularity[
                                                                 'period'])

            body = []
            curr_time = interval_start

            while curr_time < interval_end:
                timestamp = curr_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                body.append({'timestamp': timestamp,
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


class PlyQLMock(object):

    def __init__(self):
        pass

    def query(self, q, interval=None):
        if q == 'SHOW TABLES':
            return ['supervisor']
        else:
            try:
                agent_id = re.search(r'agent_id = "(.+?)"', q).group(1)
                filename = 'result_{0}.json'.format(agent_id)
                filepath = os.path.join(resources, 'plyql', filename)
                data = open(filepath).read()
                return json.loads(data)
            except (AttributeError, IOError):
                return []
