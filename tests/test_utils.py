#! /usr/bin/env python
import unittest, mock
from datetime import datetime, timedelta
from utils import (permute, haiku, haiku_permute, adjs,
    nouns, uuid, validate_ip, iso_8601_duration_to_timedelta,
    iso_8601_interval_to_datetimes)

class TestUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # http://www.voidspace.org.uk/python/mock/examples.html#partial-mocking
    @mock.patch('utils.datetime')
    def test_iso_8601_interval_to_datetimes(self, mock_datetime):
        now = datetime(2016, 1, 1)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        with self.assertRaises(ValueError) as context:
            iso_8601_interval_to_datetimes('P6Yasdf')
        self.assertIn('Malformed ISO 8601 interval', context.exception.message)
        self.assertEqual(iso_8601_interval_to_datetimes('P7Y'),
            (now - timedelta(days=365*7), None))
        self.assertEqual(iso_8601_interval_to_datetimes('P6Y5M'),
            (now - timedelta(days=(365*6 + 5 * 30)), None))

        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, '7432891')
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, 'asdf')
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, '23P7DT5H')
        self.assertEqual(iso_8601_interval_to_datetimes('1999-12-31T16:00:00.000Z'),
            (datetime(year=1999, month=12, day=31, hour=16), None))
        self.assertEqual(iso_8601_interval_to_datetimes('2016-08-01T23:10:59.111Z'),
            (datetime(year=2016, month=8, day=1, hour=23, minute=10, second=59,
                microsecond=111), None))
        
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, 'P6Yasdf/P8Y')
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, 'P7Y/asdf')
        self.assertEqual(iso_8601_interval_to_datetimes('P6Y5M/P9D'),
            (now - timedelta(days=365*6 + 5*30), now - timedelta(days=9)))
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, '7432891/1234')
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, 'asdf/87rf')
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, '23P7DT5H/89R3')
        self.assertEqual(iso_8601_interval_to_datetimes('1999-12-31T16:00:00.000Z/P5DT7H'),
            (datetime(year=1999, month=12, day=31, hour=16),
                now - timedelta(days=5, hours=7)))
        self.assertEqual(iso_8601_interval_to_datetimes('2016-08-01T23:10:59.111Z/2016-08-08T00:13:23.001Z'),
            (datetime(year=2016, month=8, day=1, hour=23, minute=10, second=59, microsecond=111),
                datetime(year=2016, month=8, day=8, hour=0, minute=13, second=23, microsecond=001)))

    def test_iso_8601_duration_to_timedelta(self):
        self.assertEqual(iso_8601_duration_to_timedelta('P3Y6M4DT12H30M5S'),
            timedelta(days=3*365 + 6 * 30 + 4,
                hours=12, minutes=30, seconds=5))
        self.assertEqual(iso_8601_duration_to_timedelta('P6M4DT12H30M15S'),
            timedelta(days=6 * 30 + 4, hours=12,
                minutes=30, seconds=15))
        self.assertEqual(iso_8601_duration_to_timedelta('P6M1DT'),
            timedelta(days=6 * 30 + 1))
        self.assertEqual(iso_8601_duration_to_timedelta('P5M3DT5S'),
            timedelta(days=5 * 30 + 3, seconds=5))
        self.assertEqual(iso_8601_duration_to_timedelta('P3Y4DT12H5S'),
            timedelta(days=365 * 3 + 4, hours=12, seconds=5))
        self.assertEqual(iso_8601_duration_to_timedelta('P3Y4DT12H30M0.5005S'),
            timedelta(days=365 * 3 + 4, hours=12, minutes=30,
                milliseconds=500, microseconds=500))
        self.assertEqual(iso_8601_duration_to_timedelta('PT.5005S'),
            timedelta(milliseconds=500, microseconds=500))
        self.assertIsNone(iso_8601_duration_to_timedelta('P6Yasdf'))
        self.assertIsNone(iso_8601_duration_to_timedelta('7432891'))
        self.assertIsNone(iso_8601_duration_to_timedelta('asdf'))
        self.assertIsNone(iso_8601_duration_to_timedelta('23P7DT5H'))
        self.assertIsNone(iso_8601_duration_to_timedelta(''))

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
