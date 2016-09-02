#! /usr/bin/env python
import unittest
import mock
from datetime import datetime, timedelta
from utils.haiku import permute, haiku, haiku_name, adjs, nouns
from utils.uuid import uuid
from utils.ip import validate_ip
from utils.iso_8601 import (iso_8601_period_to_timedelta,
                            iso_8601_interval_to_datetimes,
                            validate_iso_8601_period,
                            validate_iso_8601_interval)


class TestUtils(unittest.TestCase):
    # http://www.voidspace.org.uk/python/mock/examples.html#partial-mocking

    @mock.patch('utils.iso_8601.datetime')
    def test_iso_8601_interval_to_datetimes(self, mock_datetime):
        now = datetime(2016, 1, 1)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        with self.assertRaises(ValueError) as context:
            iso_8601_interval_to_datetimes('P6Yasdf')
        self.assertIn('Malformed ISO 8601 interval', context.exception.message)
        self.assertEqual(iso_8601_interval_to_datetimes('P7Y'),
                         (now - timedelta(days=365 * 7), None))
        self.assertEqual(iso_8601_interval_to_datetimes('P6W'),
                         (now - timedelta(days=6 * 7), None))
        self.assertEqual(iso_8601_interval_to_datetimes('P6Y5M'),
                         (now - timedelta(days=(365 * 6 + 5 * 30)), None))

        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, '7432891')
        self.assertRaises(ValueError, iso_8601_interval_to_datetimes, 'asdf')
        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, '23P7DT5H')
        self.assertEqual(
            iso_8601_interval_to_datetimes('1999-12-31T16:00:00.000Z'),
            (datetime(year=1999, month=12, day=31, hour=16), None))
        self.assertEqual(
            iso_8601_interval_to_datetimes('2016-08-01T23:10:59.111Z'),
            (datetime(year=2016, month=8, day=1, hour=23, minute=10,
                      second=59, microsecond=111), None))

        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, 'P6Yasdf/P8Y')
        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, 'P7Y/asdf')
        self.assertEqual(iso_8601_interval_to_datetimes('P6Y5M/P9D'),
                         (now - timedelta(days=365 * 6 + 5 * 30),
                          now - timedelta(days=9)))
        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, '7432891/1234')
        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, 'asdf/87rf')
        self.assertRaises(
            ValueError, iso_8601_interval_to_datetimes, '23P7DT5H/89R3')
        self.assertEqual(
            iso_8601_interval_to_datetimes('1999-12-31T16:00:00.000Z/P5DT7H'),
            (datetime(year=1999, month=12, day=31, hour=16),
             now - timedelta(days=5, hours=7)))
        self.assertEqual(
            iso_8601_interval_to_datetimes('2016-08-01T23:10:59.111Z/'
                                           '2016-08-08T00:13:23.001Z'),
            (datetime(year=2016, month=8, day=1, hour=23, minute=10,
                      second=59, microsecond=111),
             datetime(year=2016, month=8, day=8, hour=0, minute=13,
                      second=23, microsecond=001)))

    def test_validate_iso_8601_interval(self):
        self.assertTrue(validate_iso_8601_interval('P7Y'))
        self.assertTrue(validate_iso_8601_interval('P6W'))
        self.assertTrue(validate_iso_8601_interval('P6Y5M'))
        self.assertTrue(validate_iso_8601_interval('1999-12-31T16:00:00.000Z'))
        self.assertTrue(validate_iso_8601_interval('2016-08-01T23:10:59.111Z'))
        self.assertTrue(validate_iso_8601_interval('P6Y5M/P9D'))
        self.assertTrue(validate_iso_8601_interval(
            '1999-12-31T16:00:00.000Z/P5DT7H'))
        self.assertTrue(validate_iso_8601_interval(
            '2016-08-01T23:10:59.111Z/2016-08-08T00:13:23.001Z'))
        self.assertFalse(validate_iso_8601_interval('P6Yasdf'))
        self.assertFalse(validate_iso_8601_interval('7432891'))
        self.assertFalse(validate_iso_8601_interval('23P7DT5H'))
        self.assertFalse(validate_iso_8601_interval('P6Yasdf/P8Y'))
        self.assertFalse(validate_iso_8601_interval('P7Y/asdf'))
        self.assertFalse(validate_iso_8601_interval('7432891/1234'))
        self.assertFalse(validate_iso_8601_interval('asdf/87rf'))
        self.assertFalse(validate_iso_8601_interval('23P7DT5H/89R3'))

    def test_iso_8601_period_to_timedelta(self):
        self.assertEqual(iso_8601_period_to_timedelta('P3Y6M4DT12H30M5S'),
                         timedelta(days=3 * 365 + 6 * 30 + 4,
                                   hours=12, minutes=30, seconds=5))
        self.assertEqual(iso_8601_period_to_timedelta('P6M4DT12H30M15S'),
                         timedelta(days=6 * 30 + 4, hours=12,
                                   minutes=30, seconds=15))
        self.assertEqual(iso_8601_period_to_timedelta('P6M1DT'),
                         timedelta(days=6 * 30 + 1))
        self.assertEqual(iso_8601_period_to_timedelta('P6W'),
                         timedelta(weeks=6))
        self.assertEqual(iso_8601_period_to_timedelta('P5M3DT5S'),
                         timedelta(days=5 * 30 + 3, seconds=5))
        self.assertEqual(iso_8601_period_to_timedelta('P3Y4DT12H5S'),
                         timedelta(days=365 * 3 + 4, hours=12, seconds=5))
        self.assertEqual(iso_8601_period_to_timedelta('P3Y4DT12H30M0.5005S'),
                         timedelta(days=365 * 3 + 4, hours=12, minutes=30,
                                   milliseconds=500, microseconds=500))
        self.assertEqual(iso_8601_period_to_timedelta('PT.5005S'),
                         timedelta(milliseconds=500, microseconds=500))
        self.assertIsNone(iso_8601_period_to_timedelta('P6Yasdf'))
        self.assertIsNone(iso_8601_period_to_timedelta('7432891'))
        self.assertIsNone(iso_8601_period_to_timedelta('asdf'))
        self.assertIsNone(iso_8601_period_to_timedelta('23P7DT5H'))
        self.assertIsNone(iso_8601_period_to_timedelta(''))

    def test_validate_iso_8601_period(self):
        self.assertTrue(validate_iso_8601_period('P3Y6M4W7DT12H30M5S'))
        self.assertTrue(validate_iso_8601_period('P6M4DT12H30M15S'))
        self.assertTrue(validate_iso_8601_period('P6M1DT'))
        self.assertTrue(validate_iso_8601_period('P6W'))
        self.assertTrue(validate_iso_8601_period('P5M3DT5S'))
        self.assertTrue(validate_iso_8601_period('P3Y4DT12H5S'))
        self.assertTrue(validate_iso_8601_period('P3Y4DT12H30M0.5005S'))
        self.assertTrue(validate_iso_8601_period('PT.5005S'))
        self.assertFalse(validate_iso_8601_period('P6Yasdf'))
        self.assertFalse(validate_iso_8601_period('7432891'))
        self.assertFalse(validate_iso_8601_period('asdf'))
        self.assertFalse(validate_iso_8601_period('23P7DT5H'))
        self.assertFalse(validate_iso_8601_period(''))

    @mock.patch('utils.haiku.random.choice')
    def test_haiku(self, mock_choice):
        mock_choice.side_effect = [adjs[22], nouns[13], adjs[7], nouns[30]]
        (adjective, noun) = haiku()
        self.assertEqual(adjective, 'blue')
        self.assertEqual(noun, 'leaf')
        (adjective, noun) = haiku()
        self.assertEqual(adjective, 'dark')
        self.assertEqual(noun, 'flower')

    def test_permute(self):
        for i in range(9999):
            permutation = permute(i)
            self.assertTrue(permutation < 9999)
        self.assertEqual(permute(0), 7469)
        self.assertEqual(permute(3), 309)

    @mock.patch('utils.haiku.random.choice')
    def test_haiku_name(self, mock_choice):
        mock_choice.side_effect = [adjs[4], nouns[10], adjs[17], nouns[21]]
        [adjective, noun, num] = haiku_name(5).split('-')
        self.assertEqual(adjective, 'silent')
        self.assertEqual(noun, 'sunset')
        self.assertEqual(len(num), 4, 'Length of number string is 4')
        self.assertEqual(int(num), 2137, 'Integer value is 2137')
        [adjective, noun, num] = haiku_name(9000).split('-')
        self.assertEqual(adjective, 'twilight')
        self.assertEqual(noun, 'glade')
        self.assertEqual(len(num), 4, 'Length of number string is 4')
        self.assertEqual(int(num), 9384, 'Integer value is 9384')

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
