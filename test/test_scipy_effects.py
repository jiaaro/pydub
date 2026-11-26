import array
import unittest

from pydub import AudioSegment

try:
    import scipy  # noqa: F401
except ImportError:
    scipy = None


@unittest.skipIf(scipy is None, "scipy is not installed")
class ScipyEqTests(unittest.TestCase):

    def setUp(self):
        import pydub.scipy_effects  # noqa: F401

        samples = array.array("h", [1000, -1000] * 4410)
        self.stereo = AudioSegment(
            samples.tobytes(), sample_width=2, frame_rate=44100, channels=2
        )

    def test_eq_supports_every_stereo_channel_mode(self):
        for channel_mode in ("L+R", "L", "R", "M+S", "M", "S"):
            with self.subTest(channel_mode=channel_mode):
                result = self.stereo.eq(1000, 100, channel_mode=channel_mode)
                self.assertEqual(result.channels, 2)
                self.assertEqual(len(result), len(self.stereo))


if __name__ == "__main__":
    unittest.main()
