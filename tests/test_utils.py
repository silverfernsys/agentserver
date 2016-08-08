#! /usr/bin/env python
import unittest
from utils import permute, haiku, haiku_permute, adjs, nouns, uuid, validate_ip

class TestUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

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
