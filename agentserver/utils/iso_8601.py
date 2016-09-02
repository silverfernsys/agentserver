from datetime import datetime, timedelta
import re

# https://en.wikipedia.org/wiki/ISO_8601
iso_8601_interval_regex = re.compile(
    r'^(P((?P<s_i_year>(\d+(\.\d*)?|\.\d+))Y)?'
    r'((?P<s_i_month>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<s_i_week>(\d+(\.\d*)?|\.\d+))W)?'
    r'((?P<s_i_day>(\d+(\.\d*)?|\.\d+))D)?'
    r'(T((?P<s_i_hour>(\d+(\.\d*)?|\.\d+))H)?'
    r'((?P<s_i_minute>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<s_i_second>(\d+(\.\d*)?|\.\d+))S)?)?|'
    r'(?P<s_dt_year>\d{4})-(?P<s_dt_month>\d{2})-(?P<s_dt_day>\d{2})'
    r'(T(?P<s_dt_hour>\d{2}):(?P<s_dt_minute>\d{2}):'
    r'(?P<s_dt_second>(\d{2}))(\.(?P<s_dt_microsecond>\d+))?Z)?)(/'
    r'(P((?P<e_i_year>(\d+(\.\d*)?|\.\d+))Y)?'
    r'((?P<e_i_month>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<e_i_week>(\d+(\.\d*)?|\.\d+))W)?'
    r'((?P<e_i_day>(\d+(\.\d*)?|\.\d+))D)?'
    r'(T((?P<e_i_hour>(\d+(\.\d*)?|\.\d+))H)?'
    r'((?P<e_i_minute>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<e_i_second>(\d+(\.\d*)?|\.\d+))S)?)?|'
    r'(?P<e_dt_year>\d{4})-(?P<e_dt_month>\d{2})-(?P<e_dt_day>\d{2})'
    r'(T(?P<e_dt_hour>\d{2}):(?P<e_dt_minute>\d{2}):'
    r'(?P<e_dt_second>(\d{2}))(\.(?P<e_dt_microsecond>\d+))?Z)?))?$')


def iso_8601_interval_to_datetimes(interval):
    match = iso_8601_interval_regex.match(interval)
    if match:
        s_i = {k: float(v) for k, v in match.groupdict().items()
               if v and k.startswith('s_i_')}
        s_dt = {k: int(v) for k, v in match.groupdict().items()
                if v and k.startswith('s_dt_')}
        e_i = {k: float(v) for k, v in match.groupdict().items()
               if v and k.startswith('e_i_')}
        e_dt = {k: int(v) for k, v in match.groupdict().items()
                if v and k.startswith('e_dt_')}

        if len(s_i.keys()) > 0 and len(s_dt.keys()) == 0:
            start = datetime.now() - timedelta_from_dict(s_i, 's_i_')
        elif len(s_i.keys()) == 0 and len(s_dt.keys()) > 0:
            start = datetime_from_dict(s_dt, 's_dt_')
        else:
            raise ValueError('Malformed ISO 8601 interval "{0}".'.
                             format(interval))

        if len(e_i.keys()) > 0 and len(e_dt.keys()) == 0:
            end = datetime.now() - timedelta_from_dict(e_i, 'e_i_')
        elif len(e_i.keys()) == 0 and len(e_dt.keys()) > 0:
            end = datetime_from_dict(e_dt, 'e_dt_')
        elif len(e_i.keys()) == 0 and len(e_dt.keys()) == 0:
            end = None
        else:
            raise ValueError('Malformed ISO 8601 interval "{0}".'.
                             format(interval))
        return (start, end)
    else:
        raise ValueError('Malformed ISO 8601 interval "{0}".'.
                         format(interval))


def validate_iso_8601_interval(interval):
    match = iso_8601_interval_regex.match(interval)
    if match:
        return True
    else:
        return False


iso_8601_period_regex = re.compile(
    r'^P((?P<year>(\d+(\.\d*)?|\.\d+))Y)?'
    r'((?P<month>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<week>(\d+(\.\d*)?|\.\d+))W)?'
    r'((?P<day>(\d+(\.\d*)?|\.\d+))D)?'
    r'(T((?P<hour>(\d+(\.\d*)?|\.\d+))H)?'
    r'((?P<minute>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<second>(\d+(\.\d*)?|\.\d+))S)?)?$')


def iso_8601_period_to_timedelta(period):
    """ Extracts a string such as P3Y6M4DT12H30M5S to
    a timedelta object.
    NOTE: Months are converted into 30 days.
    NOTE: Years are converted into 365 days.
    """
    match = iso_8601_period_regex.match(period)
    if match:
        items = match.groupdict().items()
        return timedelta_from_dict({k: float(v)
                                    for k, v in items if v})
    else:
        return None


def validate_iso_8601_period(period):
    match = iso_8601_period_regex.match(period)
    if match:
        return True
    else:
        return False


def timedelta_from_dict(dict, prefix=''):
    return timedelta(weeks=dict.get(prefix + 'week', 0.0),
                     days=dict.get(prefix + 'day', 0.0)
                     + 30 * dict.get(prefix + 'month', 0.0)
                     + 365 * dict.get(prefix + 'year', 0.0),
                     hours=dict.get(prefix + 'hour', 0.0),
                     minutes=dict.get(prefix + 'minute', 0.0),
                     seconds=dict.get(prefix + 'second', 0.0))


def datetime_from_dict(dict, prefix=''):
    return datetime(year=dict.get(prefix + 'year', 0),
                    month=dict.get(prefix + 'month', 0),
                    day=dict.get(prefix + 'day', 0),
                    hour=dict.get(prefix + 'hour', 0),
                    minute=dict.get(prefix + 'minute', 0),
                    second=dict.get(prefix + 'second', 0),
                    microsecond=dict.get(prefix + 'microsecond', 0))


def validate_timestamp(timestamp):
    try:
        datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        return True
    except:
        return False
