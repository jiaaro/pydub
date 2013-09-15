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
        self.assertTrue(len(seg1) > 0)


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
        self.assertTrue(lower_bound < val < upper_bound,
                "%s is not in the acceptable range: %s - %s" %
                        (val, lower_bound, upper_bound))

    def assertWithinTolerance(self, val, expected, tolerance=None,
                percentage=None):
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
        self.assertAlmostEqual(ratio_to_db(quieter.rms, self.seg1.rms), -6, places=2)

        louder = quieter + 2.5
        self.assertAlmostEqual(ratio_to_db(louder.rms, quieter.rms), 2.5, places=2)

    def test_repeat_with_multiply(self):
        seg = self.seg1 * 3
        expected = len(self.seg1) * 3
        expected = (expected - 2, expected + 2)
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

        past_end = second_long_slice[:1500]
        self.assertTrue(second_long_slice._data == past_end._data)

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
        self.assertWithinTolerance(len(monomp3), len(self.seg2),
                percentage=0.01)

        merged = monomp3.append(stereo, crossfade=100)
        self.assertWithinTolerance(len(merged),
                len(self.seg1) + len(self.seg2) - 100, tolerance=1)

    def test_export(self):
        seg = self.seg1 + self.seg2

        exported_mp3 = seg.export()
        exported_wav = seg.export(format='wav')

        exported1 = AudioSegment.from_mp3(exported_mp3)
        exported2 = AudioSegment.from_wav(exported_wav)

        self.assertWithinTolerance(len(exported1), len(seg), percentage=0.01)
        self.assertWithinTolerance(len(exported2), len(seg), percentage=0.01)

    def test_export_forced_codec(self):
        seg = self.seg1 + self.seg2

        seg.export('tmp.ogg', 'ogg', codec='libvorbis')
        exported = AudioSegment.from_ogg('tmp.ogg')
        os.unlink('tmp.ogg')
        self.assertWithinTolerance(len(exported), len(seg), percentage=0.01)

    def test_fades(self):
        seg = self.seg1[:10000]
        
        # 1 ms difference in the position of the end of the fade out
        inf_end = seg.fade(start=0, end=float('inf'), to_gain=-120)
        negative_end = seg.fade(start=0, end=-1, to_gain=-120)

        self.assertWithinTolerance(inf_end.rms, negative_end.rms,
                percentage=0.001)
        self.assertTrue(negative_end.rms <= inf_end.rms)
        self.assertTrue(inf_end.rms < seg.rms)
        
        self.assertEqual(len(inf_end), len(seg))

        self.assertTrue(-3 < ratio_to_db(inf_end.rms, seg.rms) < -2)

        # use a slice out of the middle to make sure there is audio
        seg = self.seg2[20000:30000]
        fade_out = seg.fade_out(5000)
        fade_in = seg.fade_in(5000)

        self.assertTrue(0 < fade_out.rms < seg.rms)
        self.assertTrue(0 < fade_in.rms < seg.rms)

        self.assertEqual(len(fade_out), len(seg))
        self.assertEqual(len(fade_in), len(seg))

        db_at_beginning = ratio_to_db(fade_in[:1000].rms, seg[:1000].rms)
        db_at_end = ratio_to_db(fade_in[-1000:].rms, seg[-1000:].rms)
        self.assertTrue(db_at_beginning < db_at_end)

        db_at_beginning = ratio_to_db(fade_out[:1000].rms, seg[:1000].rms)
        db_at_end = ratio_to_db(fade_out[-1000:].rms, seg[-1000:].rms)
        self.assertTrue(db_at_end < db_at_beginning)
        
    def test_reverse(self):
        seg = self.seg1
        rseg = seg.reverse()
        
        # the reversed audio should be exactly equal in playback duration
        self.assertEqual(len(seg), len(rseg))
        
        r2seg = rseg.reverse()
        
        # if you reverse it twice you should get an identical AudioSegment
        self.assertEqual(seg, r2seg)
        
    def test_normalize(self):
        seg = self.seg1
        normalized = seg.normalize(0.0)
        
        self.assertEqual(len(normalized), len(seg))
        self.assertTrue(normalized.rms > seg.rms)
        self.assertWithinTolerance(normalized.max, normalized.max_possible_amplitude, percentage=0.0001)
        
    def test_for_accidental_shortening(self):
        seg = AudioSegment.from_mp3(os.path.join(data_dir, 'party.mp3'))
        seg.export('tmp.mp3')

        for i in range(10):
            AudioSegment.from_mp3('tmp.mp3').export('tmp.mp3', "mp3")

        tmp = AudioSegment.from_mp3('tmp.mp3')

        os.unlink('tmp.mp3')
        self.assertFalse(len(tmp) < len(seg))

    def test_formats(self):
        seg_m4a = AudioSegment.from_file(os.path.join(data_dir,
                'format_test.m4a'), "m4a")
        self.assertTrue(len(seg_m4a))

    def test_equal_and_not_equal(self):
        wav_file = self.seg1.export(format='wav')
        wav = AudioSegment.from_wav(wav_file)
        self.assertTrue(self.seg1 == wav)
        self.assertFalse(self.seg1 != wav)

    def test_duration(self):
        self.assertEqual(int(self.seg1.duration_seconds), 207)

        wav_file = self.seg1.export(format='wav')
        wav = AudioSegment.from_wav(wav_file)
        self.assertEqual(wav.duration_seconds, self.seg1.duration_seconds)

    def test_autodetect_format(self):
        try:
            AudioSegment.from_file(os.path.join(data_dir, 'wrong_extension.aac'), 'aac')
        except EOFError:
            pass
        except Exception as e:
            self.fail('Expected Exception is not thrown')

        # Trying to auto detect input file format
        aac_file = AudioSegment.from_file(os.path.join(data_dir, 'wrong_extension.aac'))
        self.assertEqual(int(aac_file.duration_seconds), 9)


if __name__ == "__main__":
    unittest.main()
