from __future__ import absolute_import
import binascii
import os


def uuid():
    return binascii.hexlify(os.urandom(20)).decode()
