from __future__ import division
from datetime import datetime, timedelta
from hashids import Hashids

import binascii
import os
import random
import re


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
  