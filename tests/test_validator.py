#! /usr/bin/env python
import json, os, unittest
from validator import system_stats_validator, states_validator, snapshot_validator

FIXTURES_DIR =  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

class TestSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_system_stats(self):
        text = open(os.path.join(FIXTURES_DIR, 'system_stats', 'valid_0.json')).read()
        stats = json.loads(text)['system_stats']
        self.assertTrue(system_stats_validator.validate(stats))

        text = open(os.path.join(FIXTURES_DIR, 'system_stats', 'valid_1.json')).read()
        stats = json.loads(text)['system_stats']
        self.assertTrue(system_stats_validator.validate(stats))

        text = open(os.path.join(FIXTURES_DIR, 'system_stats', 'invalid_0.json')).read()
        stats = json.loads(text)['system_stats']
        self.assertFalse(system_stats_validator.validate(stats))
        errors = system_stats_validator.errors
        self.assertEqual(errors['dist_name'], 'required field')
        self.assertEqual(errors['num_cores'], 'must be of integer type')
        self.assertEqual(errors['processor'], 'must be of string type')
        self.assertEqual(errors['memory'], 'must be of integer type')

        text = open(os.path.join(FIXTURES_DIR, 'system_stats', 'invalid_1.json')).read()
        stats = json.loads(text)['system_stats']
        self.assertFalse(system_stats_validator.validate(stats))
        errors = system_stats_validator.errors
        self.assertEqual(errors['dist_version'], 'required field')
        self.assertEqual(errors['dist_name'], 'must be of string type')
        self.assertEqual(errors['memory'], 'required field')

    def test_states(self):
        text = open(os.path.join(FIXTURES_DIR, 'states', 'valid_0.json')).read().split('\n')
        for line in text:
            state = json.loads(line)['state_update']
            self.assertTrue(states_validator.validate(state))

        text = open(os.path.join(FIXTURES_DIR, 'states', 'valid_1.json')).read().split('\n')
        for line in text:
            state = json.loads(line)['state_update']
            self.assertTrue(states_validator.validate(state))

        # text = open(os.path.join(FIXTURES_DIR, 'states', 'invalid_0.json')).read().split('\n')
        # for line in text:
        #     state = json.loads(line)['state_update']
        #     self.assertTrue(states_validator.validate(state))

        # text = open(os.path.join(FIXTURES_DIR, 'states', 'invalid_1.json')).read().split('\n')
        # for line in text:
        #     state = json.loads(line)['state_update']
        #     self.assertTrue(states_validator.validate(state))

    def test_snapshots(self):
        text = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_0.json')).read()
        for snapshot in json.loads(text)['snapshot_update']:
            self.assertTrue(snapshot_validator(snapshot))

        text = open(os.path.join(FIXTURES_DIR, 'snapshots', 'valid_1.json')).read()
        for snapshot in json.loads(text)['snapshot_update']:
            self.assertTrue(snapshot_validator(snapshot))

        # text = open(os.path.join(FIXTURES_DIR, 'snapshots', 'invalid_0.json')).read()
        # for line in text:
        #     state = json.loads(line)['snapshot_update']
        #     self.assertTrue(states_validator.validate(state))

        # text = open(os.path.join(FIXTURES_DIR, 'snapshots', 'invalid_1.json')).read()
        # for line in text:
        #     state = json.loads(line)['snapshot_update']
        #     self.assertTrue(states_validator.validate(state))
