from __future__ import division
from datetime import datetime, timedelta
from hashids import Hashids

import binascii
import os
import random
import re

iso_8601_regex = re.compile(r'P((?P<year>(\d+(\.\d*)?|\.\d+))Y)'
        r'?((?P<month>(\d+(\.\d*)?|\.\d+))M)?'
        r'((?P<day>(\d+(\.\d*)?|\.\d+))D)?'
        r'(T((?P<hour>(\d+(\.\d*)?|\.\d+))H)?'
        r'((?P<minute>(\d+(\.\d*)?|\.\d+))M)'
        r'?((?P<second>(\d+(\.\d*)?|\.\d+))S)?)?')

def iso_8601_to_timedelta(duration):
    """ Extracts a string such as P3Y6M4DT12H30M5S to
    a timedelta object.
    NOTE: Months are converted into 30 days.
    NOTE: Years are converted into 365 days.
    """
    t = {k: float(v) for k, v in iso_8601_regex.match(duration).groupdict().items() if v}
    return timedelta(weeks = t.get('week', 0),
        days = t.get('day', 0) + 30 * t.get('month', 0)
            + 365 * t.get('year', 0),
        hours = t.get('hour', 0),
        minutes = t.get('minute', 0),
        seconds = t.get('second', 0))


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
  