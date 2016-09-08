#! /usr/bin/env python
import unittest
import mock
from datetime import datetime, timedelta
from agentserver.utils.haiku import permute, haiku, haiku_name, adjs, nouns
from agentserver.utils.uuid import uuid
from agentserver.utils.ip import validate_ip


class TestUtils(unittest.TestCase):
    @mock.patch('agentserver.utils.haiku.random.choice')
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

    @mock.patch('agentserver.utils.haiku.random.choice')
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
