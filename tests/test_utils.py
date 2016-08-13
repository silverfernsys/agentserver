#! /usr/bin/env python
from datetime import timedelta
import unittest
from utils import (permute, haiku, haiku_permute, adjs,
    nouns, uuid, validate_ip, iso_8601_to_timedelta)

class TestUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_iso_8601_to_timedelta(self):
        self.assertEqual(iso_8601_to_timedelta('P3Y6M4DT12H30M5S'),
            timedelta(days=3*365 + 6 * 30 + 4,
                hours=12, minutes=30, seconds=5))
        self.assertEqual(iso_8601_to_timedelta('P6M4DT12H30M15S'),
            timedelta(days=6 * 30 + 4, hours=12,
                minutes=30, seconds=15))
        self.assertEqual(iso_8601_to_timedelta('P6M1DT'),
            timedelta(days=6 * 30 + 1))
        self.assertEqual(iso_8601_to_timedelta('P5M3DT5S'),
            timedelta(days=5 * 30 + 3, seconds=5))
        self.assertEqual(iso_8601_to_timedelta('P3Y4DT12H5S'),
            timedelta(days=365 * 3 + 4, hours=12, seconds=5))
        self.assertEqual(iso_8601_to_timedelta('P3Y4DT12H30M0.5005S'),
            timedelta(days=365 * 3 + 4, hours=12, minutes=30,
                milliseconds=500, microseconds=500))
        self.assertEqual(iso_8601_to_timedelta('PT.5005S'),
            timedelta(milliseconds=500, microseconds=500))

    def test_haiku(self):
        h = haiku()
        self.assertIn('-', h, 'Haiku has a separator between adjective and noun')
        adjective = h.split('-')[0]
        noun = h.split('-')[1]
        self.assertIn(adjective, adjs, 'Adjective is in adj list')
        self.assertIn(noun, nouns, 'Noun is in noun list')

    def test_permute(self):
        for i in range(9999):
            permutation = permute(i)
            # print('%d - %d' % (i, permutation))
            self.assertTrue(permutation < 9999)

    def test_haiku_permute(self):
        hp = haiku_permute(0)
        num = hp.split('-')[-1]
        self.assertEqual(len(str(num)), 4, 'Length of number string is 4')
        self.assertEqual(int(num), 7469, 'Integer value is 7469')
        hp = haiku_permute(3)
        num = hp.split('-')[-1]
        self.assertEqual(len(str(num)), 4, 'Length of number string is 4')
        self.assertEqual(int(num), 309, 'Integer value is 309')

    def test_uuid(self):
        id = uuid()
        self.assertEqual(len(id), 40)

    def test_validate_ip(self):
        self.assertTrue(validate_ip('10.0.1.1'))
        self.assertTrue(validate_ip('2001:cdba:0000:0000:0000:0000:3257:9652'))
        self.assertTrue(validate_ip('2001:cdba:0:0:0:0:3257:9652'))
        self.assertTrue(validate_ip('2001:cdba::3257:9652'))
        self.assertTrue(validate_ip('2001:db8:85a3:8d3:1319:8a2e:370:7348'))
        self.assertFalse(validate_ip('4.4.4'))
