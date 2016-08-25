import binascii
import os
import random

def uuid():
    return binascii.hexlify(os.urandom(20)).decode()