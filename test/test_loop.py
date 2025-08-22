import pytest
from pydub import AudioSegment as _AS
if not hasattr(_AS, "loop"):
    pytest.skip("AudioSegment.loop not available on this branch", allow_module_level=True)
import unittest

from pydub.generators import Sine
from pydub.utils import audioop


class LoopFeatureTests(unittest.TestCase):
    def test_loop_repeats_length(self):
        seg = Sine(440).to_audio_segment(duration=100)
        out = seg.loop(count=3, crossfade=0)
        assert len(out) == 300

    @unittest.skipIf(audioop is None, "audioop not available on this Python version")
    def test_loop_with_crossfade_shortens(self):
        seg = Sine(440).to_audio_segment(duration=200)
        out = seg.loop(count=2, crossfade=50)
        assert len(out) == 200 + 200 - 50

    def test_loop_trim_to(self):
        seg = Sine(440).to_audio_segment(duration=200)
        out = seg.loop(count=10, crossfade=0, trim_to=650)
        assert len(out) == 650

    def test_loop_end_padding(self):
        seg = Sine(440).to_audio_segment(duration=200)
        out = seg.loop(count=1, end_padding=300)
        assert len(out) == 500


if __name__ == "__main__":
    unittest.main()

