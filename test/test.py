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


test1 = test2 = test3 = None
class AudioSegmentTests(unittest.TestCase):
        
    def setUp(self):
        global test1, test2, test3
        if not test1:
            test1 = AudioSegment.from_mp3(os.path.join(data_dir, 'test1.mp3'))
            test2 = AudioSegment.from_mp3(os.path.join(data_dir, 'test2.mp3'))
            test3 = AudioSegment.from_mp3(os.path.join(data_dir, 'test3.mp3'))
        self.seg1, self.seg2, self.seg3 = test1, test2, test3 


    def assertWithinRange(self, val, lower_bound, upper_bound):
        self.assertTrue(lower_bound < val < upper_bound, "%s is not in the acceptable range: %s - %s" % (val, lower_bound, upper_bound))

        
    def assertWithinTolerance(self, val, expected, tolerance=None, percentage=None):
        if percentage is not None:
            tolerance = val * percentage
        lower_bound = val - tolerance
        upper_bound = val + tolerance
        self.assertWithinRange(val, lower_bound, upper_bound)


    def test_concat(self):
        catted_audio = self.seg1 + self.seg2
        
        expected = len(self.seg1) + len(self.seg2)
        self.assertWithinTolerance(len(catted_audio), expected, 1)
        
        
    def test_append(self):
        merged1 = self.seg3.append(self.seg1, crossfade=100)
        merged2 = self.seg3.append(self.seg2, crossfade=100)
        
        self.assertEqual(len(merged1), len(self.seg1) + len(self.seg3) - 100)
        self.assertEqual(len(merged2), len(self.seg2) + len(self.seg3) - 100)
    
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
        
        
    def test_overlay(self):
        seg_mult = self.seg1[:5000] * self.seg2[:3000]
        seg_over = self.seg1[:5000].overlay(self.seg2[:3000], loop=True)
        
        self.assertEqual(len(seg_mult), len(seg_over))
        self.assertTrue(seg_mult._data == seg_over._data)
        
        self.assertEqual(len(seg_mult), 5000)
        self.assertEqual(len(seg_over), 5000)
        
        
    def test_slicing(self):
        empty = self.seg1[:0]
        second_long_slice = self.seg1[:1000]
        remainder = self.seg1[1000:]
        
        self.assertEqual(len(empty), 0)
        self.assertEqual(len(second_long_slice), 1000)
        self.assertEqual(len(remainder), len(self.seg1) - 1000)
        
        last_5_seconds = self.seg1[-5000:]
        before = self.seg1[:-5000]
        
        self.assertEqual(len(last_5_seconds), 5000)
        self.assertEqual(len(before), len(self.seg1) - 5000)
        
    
    def test_indexing(self):
        short = self.seg1[:100]

        rebuilt1 = self.seg1[:0]
        for part in short:
            rebuilt1 += part
            
        rebuilt2 = sum([part for part in short], short[:0])
        
        self.assertTrue(short._data == rebuilt1._data)
        self.assertTrue(short._data == rebuilt2._data)
        
        
    def test_set_channels(self):
        mono = self.seg1.set_channels(1)
        stereo = mono.set_channels(2)
        
        self.assertEqual(len(self.seg1), len(mono))
        self.assertEqual(len(self.seg1), len(stereo))
        
        mono = self.seg2.set_channels(1)
        mono = mono.set_frame_rate(22050)
        
        self.assertEqual(len(mono), len(self.seg2))
        
        monomp3 = AudioSegment.from_mp3(mono.export())
        self.assertWithinTolerance(len(monomp3), len(self.seg2), percentage=0.01)
        
        merged = monomp3.append(stereo, crossfade=100)
        self.assertWithinTolerance(len(merged), len(self.seg1)+len(self.seg2)-100, tolerance=1)
        
        
    def test_export(self):
        seg = self.seg1 + self.seg2
        
        exported_mp3 = seg.export()
        
        exported = AudioSegment.from_mp3(exported_mp3)
        self.assertWithinTolerance(len(exported), len(seg), percentage=0.01)


    def test_fades(self):
        # 1 ms difference in the position of the end of the fade out
        inf_end = self.seg1.fade(start=0, end=float('inf'), to_gain=-120)
        negative_end = self.seg1.fade(start=0, end=-1, to_gain=-120)
        
        self.assertWithinTolerance(inf_end.rms, negative_end.rms, percentage=0.001)
        self.assertTrue(inf_end.rms < negative_end.rms)
        self.assertTrue(inf_end.rms < self.seg1.rms)
        self.assertEqual(len(inf_end), len(self.seg1))
        
        self.assertTrue(-3 < ratio_to_db(inf_end.rms, self.seg1.rms) < -2)
        
        fade_out = self.seg1.fade_out(5000)
        fade_in = self.seg2.fade_in(5000)
        
        self.assertTrue(0 < fade_out.rms < self.seg1.rms)
        self.assertTrue(0 < fade_in.rms < self.seg2.rms)
        
        self.assertEqual(len(fade_out), len(self.seg1))
        self.assertEqual(len(fade_in), len(self.seg2))



if __name__ == "__main__":
    unittest.main()
    