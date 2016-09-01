#! /usr/bin/env python
import unittest, sys, os, logging

sys.path.insert(0, os.path.join(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0], 'agentserver'))
logging.disable(logging.CRITICAL)

testmodules = [
    # 'test_admin',
    # 'test_db',
    # 'test_http',
    # 'test_validators',
    'test_ws',
    # 'test_utils',
    ]

suite = unittest.TestSuite()

for t in testmodules:
    try:
        # If the module defines a suite() function, call it to get the suite.
        mod = __import__(t, globals(), locals(), ['suite'])
        suitefn = getattr(mod, 'suite')
        suite.addTest(suitefn())
    except (ImportError, AttributeError):
        # else, just load all the test cases from the module.
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))

unittest.TextTestRunner().run(suite)