import unittest
import os

from pydub import AudioSegment
from pydub.utils import db_to_float, ratio_to_db

data_dir = os.path.join(os.path.dirname(__file__), 'data')


class UtilityTests(unittest.TestCase):
    
    def test_db_float_conversions(self):
        self.assertEqual(db_to_float(10), 10)
        self.assertEqual(db_to_float(0), 1)
        self.assertEqual(ratio_to_db(1), 0)
        self.assertEqual(ratio_to_db(10), 10)
        self.assertEqual(3, db_to_float(ratio_to_db(3)))
        self.assertEqual(12, ratio_to_db(db_to_float(12)))
        


class FileAccessTests(unittest.TestCase):

    def setUp(self):
        self.mp3_path = os.path.join(data_dir, 'test1.mp3')
        

    def test_audio_segment_from_mp3(self):
        seg1 = AudioSegment.from_mp3(os.path.join(data_dir, 'test1.mp3'))
        
        mp3_file = open(os.path.join(data_dir, 'test1.mp3'), 'rb')
        seg2 = AudioSegment.from_mp3(mp3_file)
        
        self.assertEqual(len(seg1), len(seg2))
        self.assertTrue(seg1._data == seg2._data)



class AudioSegmentTests(unittest.TestCase):
        
    def setUp(self):
        self.seg1 = AudioSegment.from_mp3(os.path.join(data_dir, 'test1.mp3'))
        self.seg2 = AudioSegment.from_mp3(os.path.join(data_dir, 'test2.mp3'))


    def assertWithinRange(self, val, lower_bound, upper_bound):
        self.assertTrue(lower_bound < val < upper_bound, "%s is not in the acceptable range: %s - %s" % (val, lower_bound, upper_bound))

        
    def assertWithinTolerance(self, val, expected, tolerance=None, percentage=None):
        if percentage is not None:
            tolerance = val * percentage
        lower_bound = val - tolerance
        upper_bound = val + tolerance
        self.assertWithinRange(val, lower_bound, upper_bound)


    def test_concat_with_add(self):
        catted_audio = self.seg1 + self.seg2
        
        expected = len(self.seg1) + len(self.seg2)
        self.assertWithinTolerance(len(catted_audio), expected, 1)
        
    
    def test_volume_with_add_sub(self):
        quieter = self.seg1 - 6
        self.assertAlmostEqual(ratio_to_db(quieter.rms, self.seg1.rms), -6)
        
        louder = quieter + 2.5
        self.assertAlmostEqual(ratio_to_db(louder.rms, quieter.rms), 2.5)
        
        
        
    def test_repeat_with_multiply(self):
        seg = self.seg1 * 3
        expected = len(self.seg1) * 3
        expected = (expected-2, expected+2)
        self.assertTrue(expected[0] < len(seg) < expected[1])
        
        
    def test_overlay_with_multiply(self):
        seg = self.seg1 * self.seg2
        self.assertEqual(len(seg), len(self.seg1))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()