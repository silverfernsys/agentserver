#! /usr/bin/env python
import json
import os
import unittest
from agentserver.utils.validators import (system_stats_validator,
                              states_validator,
                              snapshot_validator)

resources = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), 'resources')


class TestSchema(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_system_stats(self):
        text = open(os.path.join(
            resources, 'system_stats', 'valid_0.json')).read()
        stats = json.loads(text)['system']
        self.assertTrue(system_stats_validator.validate(stats))

        text = open(os.path.join(
            resources, 'system_stats', 'valid_1.json')).read()
        stats = json.loads(text)['system']
        self.assertTrue(system_stats_validator.validate(stats))

        text = open(os.path.join(
            resources, 'system_stats', 'invalid_0.json')).read()
        stats = json.loads(text)['system']
        self.assertFalse(system_stats_validator.validate(stats))
        errors = system_stats_validator.errors
        self.assertEqual(errors['dist_name'], 'required field')
        self.assertEqual(errors['num_cores'], 'must be of integer type')
        self.assertEqual(errors['processor'], 'must be of string type')
        self.assertEqual(errors['memory'], 'must be of integer type')

        text = open(os.path.join(
            resources, 'system_stats', 'invalid_1.json')).read()
        stats = json.loads(text)['system']
        self.assertFalse(system_stats_validator.validate(stats))
        errors = system_stats_validator.errors
        self.assertEqual(errors['dist_version'], 'required field')
        self.assertEqual(errors['dist_name'], 'must be of string type')
        self.assertEqual(errors['memory'], 'required field')

    def test_states(self):
        text = open(os.path.join(resources, 'states',
                                 'valid_0.json')).read().split('\n')
        for line in text:
            state = json.loads(line)['state']
            self.assertTrue(states_validator.validate(state))

        text = open(os.path.join(resources, 'states',
                                 'valid_1.json')).read().split('\n')
        for line in text:
            state = json.loads(line)['state']
            self.assertTrue(states_validator.validate(state))

        text = open(os.path.join(resources, 'states',
                                 'invalid_0.json')).read().split('\n')
        for line in text:
            state = json.loads(line)['state']
            self.assertFalse(states_validator.validate(state))

        text = open(os.path.join(resources, 'states',
                                 'invalid_1.json')).read().split('\n')
        for line in text:
            state = json.loads(line)['state']
            self.assertFalse(states_validator.validate(state))

    def test_snapshots(self):
        text = open(os.path.join(
            resources, 'snapshots', 'valid_0.json')).read()
        self.assertTrue(snapshot_validator.validate(json.loads(text)))

        text = open(os.path.join(
            resources, 'snapshots', 'valid_1.json')).read()
        self.assertTrue(snapshot_validator.validate(json.loads(text)))

        text = open(os.path.join(
            resources, 'snapshots', 'invalid_0.json')).read()
        self.assertFalse(states_validator.validate(json.loads(text)))

        text = open(os.path.join(
            resources, 'snapshots', 'invalid_1.json')).read()
        self.assertFalse(states_validator.validate(json.loads(text)))
