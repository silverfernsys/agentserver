#! /usr/bin/env python
from pydruid.client import PyDruid
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension

from datetime import datetime, timedelta
import json

if __name__ == '__main__':
    query = PyDruid('http://localhost:8082', 'druid/v2/')

    # top = query.topn(
    #     datasource='twitterstream',
    #     granularity='all',
    #     intervals='2014-03-03/p1d',  # utc time of 2014 oscars
    #     aggregations={'count': doublesum('count')},
    #     dimension='user_mention_name',
    #     filter=(Dimension('user_lang') == 'en') & (Dimension('first_hashtag') == 'oscars') &
    #            (Dimension('user_time_zone') == 'Pacific Time (US & Canada)') &
    #            ~(Dimension('user_mention_name') == 'No Mention'),
    #     metric='count',
    #     threshold=10
    # )

    intervals = '{0}/p6w'.format((datetime.utcnow() - timedelta(weeks=6)).strftime("%Y-%m-%d"))
    # intervals = '{0}/{1}'.format((datetime.utcnow() - timedelta(weeks=8)).strftime("%Y-%m-%d"),
        # (datetime.utcnow()).strftime("%Y-%m-%d"))
    # intervals = '2016-01-01/2016-12-31'

    # top = query.topn(
    #     datasource='supervisor',
    #     granularity='all',
    #     intervals=intervals,
    #     aggregations={'count': doublesum('count')},
    #     dimension='process_name',
    #     filter=(Dimension('agent_id') == 1),
    #     metric='count',
    #     threshold=10
    # )

    # print(top.result_json)
    # print json.dumps(top.query_dict, indent=2)

    group = query.groupby(
        datasource='supervisor',
        granularity='all',
        intervals=intervals,
        dimensions=["process_name"],
        filter=(Dimension("agent_id") == 1),
        aggregations={"count": doublesum("count")}
    )

    print(group.result_json)
