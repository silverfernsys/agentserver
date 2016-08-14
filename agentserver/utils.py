from __future__ import division
from datetime import datetime, timedelta
from hashids import Hashids

import binascii
import os
import random
import re

iso_8601_interval_regex = re.compile(
    r'^(P((?P<s_i_year>(\d+(\.\d*)?|\.\d+))Y)?'
    r'((?P<s_i_month>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<s_i_day>(\d+(\.\d*)?|\.\d+))D)?'
    r'(T((?P<s_i_hour>(\d+(\.\d*)?|\.\d+))H)?'
    r'((?P<s_i_minute>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<s_i_second>(\d+(\.\d*)?|\.\d+))S)?)?|'
    r'(?P<s_dt_year>\d{4})-(?P<s_dt_month>\d{2})-(?P<s_dt_day>\d{2})'
    r'(T(?P<s_dt_hour>\d{2}):(?P<s_dt_minute>\d{2}):'
    r'(?P<s_dt_second>(\d{2}))(\.(?P<s_dt_microsecond>\d+))?Z)?)(/'
    r'(P((?P<e_i_year>(\d+(\.\d*)?|\.\d+))Y)?'
    r'((?P<e_i_month>(\d+(\.\d*)?|\.\d+))M)?'
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
        s_i = {k: float(v) for k, v in match.groupdict().items() if v and k.startswith('s_i_')}
        s_dt = {k: int(v) for k, v in match.groupdict().items() if v and k.startswith('s_dt_')}
        e_i = {k: float(v) for k, v in match.groupdict().items() if v and k.startswith('e_i_')}
        e_dt = {k: int(v) for k, v in match.groupdict().items() if v and k.startswith('e_dt_')}

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


iso_8601_duration_regex = re.compile(
    r'^P((?P<year>(\d+(\.\d*)?|\.\d+))Y)?'
    r'((?P<month>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<day>(\d+(\.\d*)?|\.\d+))D)?'
    r'(T((?P<hour>(\d+(\.\d*)?|\.\d+))H)?'
    r'((?P<minute>(\d+(\.\d*)?|\.\d+))M)?'
    r'((?P<second>(\d+(\.\d*)?|\.\d+))S)?)?$')

def iso_8601_duration_to_timedelta(duration):
    """ Extracts a string such as P3Y6M4DT12H30M5S to
    a timedelta object.
    NOTE: Months are converted into 30 days.
    NOTE: Years are converted into 365 days.
    """
    match = iso_8601_duration_regex.match(duration)
    if match:
        return timedelta_from_dict({k: float(v)
            for k, v in match.groupdict().items() if v})
    else:
        return None


def timedelta_from_dict(dict, prefix=''):
    return timedelta(weeks = dict.get(prefix + 'week', 0.0),
        days = dict.get(prefix + 'day', 0.0)
            + 30 * dict.get(prefix + 'month', 0.0)
            + 365 * dict.get(prefix + 'year', 0.0),
        hours = dict.get(prefix + 'hour', 0.0),
        minutes = dict.get(prefix + 'minute', 0.0),
        seconds = dict.get(prefix + 'second', 0.0))


def datetime_from_dict(dict, prefix=''):
    return datetime(year = dict.get(prefix + 'year', 0),
        month = dict.get(prefix + 'month', 0),
        day = dict.get(prefix + 'day', 0),
        hour = dict.get(prefix + 'hour', 0),
        minute = dict.get(prefix + 'minute', 0),
        second = dict.get(prefix + 'second', 0),
        microsecond=dict.get(prefix + 'microsecond', 0))


def uuid():
    return binascii.hexlify(os.urandom(20)).decode()


adjs = [
    "autumn", "hidden", "bitter", "misty", "silent", "empty", "dry", "dark",
    "summer", "icy", "delicate", "quiet", "white", "cool", "spring", "winter",
    "patient", "twilight", "dawn", "crimson", "wispy", "weathered", "blue",
    "billowing", "broken", "cold", "damp", "falling", "frosty", "green",
    "long", "late", "lingering", "bold", "little", "morning", "muddy", "old",
    "red", "rough", "still", "small", "sparkling", "throbbing", "shy",
    "wandering", "withered", "wild", "black", "young", "holy", "solitary",
    "fragrant", "aged", "snowy", "proud", "floral", "restless", "divine",
    "polished", "ancient", "purple", "lively", "nameless"
 ]


nouns = [
    "waterfall", "river", "breeze", "moon", "rain", "wind", "sea", "morning",
    "snow", "lake", "sunset", "pine", "shadow", "leaf", "dawn", "glitter",
    "forest", "hill", "cloud", "meadow", "sun", "glade", "bird", "brook",
    "butterfly", "bush", "dew", "dust", "field", "fire", "flower", "firefly",
    "feather", "grass", "haze", "mountain", "night", "pond", "darkness",
    "snowflake", "silence", "sound", "sky", "shape", "surf", "thunder",
    "violet", "water", "wildflower", "wave", "water", "resonance", "sun",
    "wood", "dream", "cherry", "tree", "fog", "frost", "voice", "paper",
    "frog", "smoke", "star"
]


# http://preshing.com/20121224/how-to-generate-a-sequence-of-unique-random-integers/
def permute(x):
    """
    permute returns a number in the range 0 to 9999
    that is unique for each x
    """
    prime = 9887 # https://primes.utm.edu/lists/small/10000.txt
    offset = 453
    maximum = 9999
    x = (x + offset) % maximum
    if (x >= prime):
        return x
    else:
        residue = (x * x) % prime
        if x <= (prime / 2):
            return residue
        else:
            return prime - residue


def haiku(separator='-'):
    adj = random.choice(adjs)
    noun = random.choice(nouns)
    return '{adj}{separator}{noun}'.format(
         adj=adj,
         noun=noun,
         separator=separator)


def haiku_permute(id, separator='-'):
    return '{h}{separator}{p}'.format(
        h=haiku(separator),
        separator=separator,
        p=str(permute(id)).rjust(4,'0'))


def validate_ip(ip):
    """
    Validates an IPv4 or IPv6 IP address
    """
    regex = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|' \
        '(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}| ' \
            '([0-9a-fA-F]{1,4}:){1,7}:|' \
            '([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|' \
            '([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|' \
            '([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|' \
            '([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|' \
            '([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|' \
            '[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|' \
            ':((:[0-9a-fA-F]{1,4}){1,7}|:)|' \
            'fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|' \
            '::(ffff(:0{1,4}){0,1}:){0,1}' \
            '((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}' \
            '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|' \
            '([0-9a-fA-F]{1,4}:){1,4}:' \
            '((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}' \
            '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])' \
            ')')
    if regex.match(ip):
        return True
    else:
        return False
  