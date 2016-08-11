#! /usr/bin/env python
from pydruid.client import PyDruid
from pydruid.utils.aggregators import doublesum, longsum
from pydruid.utils.filters import Dimension

from datetime import datetime, timedelta
import json

def longmax(raw_metric):
    return {"type": "longMax", "fieldName": raw_metric} 

def doublemax(raw_metric):
    return {"type": "doubleMax", "fieldName": raw_metric} 

if __name__ == '__main__':
    query = PyDruid('http://localhost:8082', 'druid/v2/')
    intervals = '{0}/p6w'.format((datetime.utcnow() - timedelta(weeks=6)).strftime("%Y-%m-%d"))

    timeseries = query.timeseries(
        datasource='supervisor',
        granularity='none',
        # granularity='hour',
        # granularity={'type': 'period', 'period': 'PT2H'},
        descending= False,
        intervals=intervals,
        aggregations={'cpu': doublemax('cpu'), 'mem': longmax('mem')},
        context={'skipEmptyBuckets': 'true'},
        filter=(Dimension('agent_id') == 1) & (Dimension('process_name') == 'process_1')
    )

    print(json.dumps(timeseries.result, indent=2))

    select = query.select(
        datasource='supervisor',
        granularity='all',
        intervals=intervals,
        descending= True,
        dimensions=['process_name'],
        metrics=['cpu', 'mem'],
        filter=(Dimension('agent_id') == 1) & (Dimension('process_name') == 'process_1'),
        paging_spec={'pagingIdentifiers': {}, "threshold":1}
    )

    print(json.dumps(select.result, indent=2))
