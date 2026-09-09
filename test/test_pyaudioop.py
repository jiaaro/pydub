"""
Differential tests: pydub's pure-Python audioop replacement must produce
exactly what the C module produces, for every function pydub uses, in both
the NumPy and plain-Python code paths. Skipped when no C audioop is
importable (Python 3.13+ without audioop-lts).
"""
import random
import struct
import unittest

try:
    import audioop as c_audioop
except ImportError:
    c_audioop = None

from pydub import pyaudioop

try:
    import numpy
except ImportError:
    numpy = None


def random_fragment(rng, size, nsamples):
    lo, hi = pyaudioop._MINVALS[size], pyaudioop._MAXVALS[size]
    # bias toward extremes so clamping and wrap-around get exercised
    vals = []
    for _ in range(nsamples):
        r = rng.random()
        if r < 0.1:
            vals.append(lo)
        elif r < 0.2:
            vals.append(hi)
        else:
            vals.append(rng.randint(lo, hi))
    return pyaudioop._pack_py(vals, size)


@unittest.skipIf(c_audioop is None, "no C audioop available to compare against")
class PyAudioopMatchesC(unittest.TestCase):
    SIZES = (1, 2, 3, 4)

    def run_both(self, check):
        # run with numpy (if available) and without
        saved = pyaudioop.use_numpy
        try:
            if numpy is not None:
                pyaudioop.use_numpy = True
                check("numpy")
            pyaudioop.use_numpy = False
            check("python")
        finally:
            pyaudioop.use_numpy = saved

    def fragments(self, size, count=6, maxlen=400):
        rng = random.Random(1234 + size)
        for _ in range(count):
            yield random_fragment(rng, size, rng.randint(0, maxlen))

    def test_queries(self):
        def check(mode):
            for size in self.SIZES:
                for frag in self.fragments(size):
                    self.assertEqual(pyaudioop.max(frag, size), c_audioop.max(frag, size), (mode, size, "max"))
                    self.assertEqual(pyaudioop.minmax(frag, size), c_audioop.minmax(frag, size), (mode, size, "minmax"))
                    self.assertEqual(pyaudioop.avg(frag, size), c_audioop.avg(frag, size), (mode, size, "avg"))
                    self.assertEqual(pyaudioop.cross(frag, size), c_audioop.cross(frag, size), (mode, size, "cross"))
                    mine, ref = pyaudioop.rms(frag, size), c_audioop.rms(frag, size)
                    if size == 4:
                        # 32-bit squares exceed double precision; C accumulates
                        # sequentially and rounds differently in the last place
                        self.assertLessEqual(abs(mine - ref), 1, (mode, size, "rms"))
                    else:
                        self.assertEqual(mine, ref, (mode, size, "rms"))
                    if len(frag):
                        i = len(frag) // size // 2
                        self.assertEqual(pyaudioop.getsample(frag, size, i), c_audioop.getsample(frag, size, i))
        self.run_both(check)

    def test_mul(self):
        def check(mode):
            for size in self.SIZES:
                for frag in self.fragments(size):
                    for factor in (0.0, 0.5, 1.0, 1.7, -1.0, -2.5, 3.0, 0.123456):
                        self.assertEqual(pyaudioop.mul(frag, size, factor),
                                         c_audioop.mul(frag, size, factor), (mode, size, factor))
        self.run_both(check)

    def test_mono_stereo(self):
        def check(mode):
            for size in self.SIZES:
                for frag in self.fragments(size):
                    if (len(frag) // size) % 2:
                        frag = frag[:-size]
                    for f1, f2 in ((0.5, 0.5), (1, 0), (0, 1), (1.0, 1.0)):
                        self.assertEqual(pyaudioop.tomono(frag, size, f1, f2),
                                         c_audioop.tomono(frag, size, f1, f2), (mode, size, "tomono"))
                        self.assertEqual(pyaudioop.tostereo(frag, size, f1, f2),
                                         c_audioop.tostereo(frag, size, f1, f2), (mode, size, "tostereo"))
                    # With inexact factors the C build may fuse the multiply-add
                    # (FMA on arm64), which can move a value across a floor
                    # boundary; allow one LSB per sample there.
                    mine = pyaudioop._samples_py(pyaudioop.tomono(frag, size, -0.3, 1.2), size)
                    ref = pyaudioop._samples_py(c_audioop.tomono(frag, size, -0.3, 1.2), size)
                    self.assertEqual(len(mine), len(ref))
                    for a, b in zip(mine, ref):
                        self.assertLessEqual(abs(a - b), 1, (mode, size, "tomono fma"))
        self.run_both(check)

    def test_add_bias_reverse_byteswap(self):
        def check(mode):
            for size in self.SIZES:
                frags = list(self.fragments(size))
                for a in frags:
                    b = random_fragment(random.Random(len(a)), size, len(a) // size)
                    self.assertEqual(pyaudioop.add(a, b, size), c_audioop.add(a, b, size), (mode, size, "add"))
                    for bias in (0, 1, -1, 128, -128, 1000, -70000, 0x7FFFFFFF):
                        self.assertEqual(pyaudioop.bias(a, size, bias), c_audioop.bias(a, size, bias), (mode, size, bias))
                    self.assertEqual(pyaudioop.reverse(a, size), c_audioop.reverse(a, size), (mode, size, "reverse"))
                    self.assertEqual(pyaudioop.byteswap(a, size), c_audioop.byteswap(a, size), (mode, size, "byteswap"))
        self.run_both(check)

    def test_lin2lin(self):
        def check(mode):
            for size in self.SIZES:
                for frag in self.fragments(size):
                    for size2 in self.SIZES:
                        self.assertEqual(pyaudioop.lin2lin(frag, size, size2),
                                         c_audioop.lin2lin(frag, size, size2), (mode, size, size2))
        self.run_both(check)

    def test_ratecv(self):
        rates = [(44100, 48000), (48000, 44100), (44100, 22050), (8000, 44100),
                 (22050, 11025), (11025, 22050), (44100, 44100), (96000, 16000), (3, 7)]

        def check(mode):
            for size in (1, 2, 3, 4):
                for nch in (1, 2, 3):
                    rng = random.Random(99 + size * 10 + nch)
                    for inrate, outrate in rates:
                        nframes = rng.randint(0, 300)
                        frag = random_fragment(rng, size, nframes * nch)
                        mine = pyaudioop.ratecv(frag, size, nch, inrate, outrate, None)
                        ref = c_audioop.ratecv(frag, size, nch, inrate, outrate, None)
                        self.assertEqual(mine, ref, (mode, size, nch, inrate, outrate, nframes))
                        # continue with the returned state, like streaming callers do
                        frag2 = random_fragment(rng, size, rng.randint(1, 100) * nch)
                        mine2 = pyaudioop.ratecv(frag2, size, nch, inrate, outrate, mine[1])
                        ref2 = c_audioop.ratecv(frag2, size, nch, inrate, outrate, ref[1])
                        self.assertEqual(mine2, ref2, (mode, size, nch, inrate, outrate, "state"))
                    # the recursive filter path
                    frag = random_fragment(rng, size, 200 * nch)
                    self.assertEqual(pyaudioop.ratecv(frag, size, nch, 44100, 32000, None, 3, 2),
                                     c_audioop.ratecv(frag, size, nch, 44100, 32000, None, 3, 2), (mode, size, nch, "filter"))
        self.run_both(check)

    def test_errors(self):
        for fn in (pyaudioop.max, pyaudioop.rms, pyaudioop.avg):
            self.assertRaises(pyaudioop.error, fn, b"\0\0\0", 2)
            self.assertRaises(pyaudioop.error, fn, b"\0\0\0\0", 5)
        self.assertRaises(pyaudioop.error, pyaudioop.add, b"\0\0", b"\0\0\0\0", 2)
        self.assertRaises(pyaudioop.error, pyaudioop.tomono, b"\0\0", 2, 1, 1)
        self.assertRaises(pyaudioop.error, pyaudioop.ratecv, b"\0\0", 2, 1, 0, 8000, None)
        self.assertRaises(NotImplementedError, pyaudioop.lin2ulaw, b"\0\0", 2)


class PyAudioopStandalone(unittest.TestCase):
    """Sanity checks that do not need the C module."""

    def test_basic_values(self):
        frag = struct.pack("<4h", 100, -200, 300, -32768)
        self.assertEqual(pyaudioop.max(frag, 2), 32768)
        self.assertEqual(pyaudioop.minmax(frag, 2), (-32768, 300))
        self.assertEqual(pyaudioop.mul(frag, 2, 2.0), struct.pack("<4h", 200, -400, 600, -32768))
        self.assertEqual(pyaudioop.bias(b"\x7f\x80", 1, 1), b"\x80\x81")
        self.assertEqual(pyaudioop.lin2lin(b"\x01\x02", 1, 2), struct.pack("<2h", 0x100, 0x200))
        self.assertEqual(pyaudioop.tostereo(b"\x01", 1, 1, 0), b"\x01\x00")
        self.assertEqual(pyaudioop.tomono(b"\x02\x04", 1, 0.5, 0.5), b"\x03")
        out, state = pyaudioop.ratecv(struct.pack("<4h", 0, 1000, 2000, 3000), 2, 1, 8000, 16000, None)
        # 4 frames in at 1:2 yield 7 frames out; the eighth waits for the next call
        self.assertEqual(len(out), 14)
        self.assertLess(state[0], 0)
        out2, state2 = pyaudioop.ratecv(struct.pack("<2h", 4000, 5000), 2, 1, 8000, 16000, state)
        self.assertEqual(len(out2), 8)


if __name__ == "__main__":
    unittest.main()
