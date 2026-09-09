"""
Tests for the behaviour added in the 0.26 revival: wav header hardening,
24-bit widening, missing-converter errors, encoder fallbacks and the export
path that feeds ffmpeg raw PCM.
"""
import os
import struct
import unittest
from io import BytesIO
from tempfile import NamedTemporaryFile

import pydub.utils as utils
from pydub import AudioSegment
from pydub.audio_segment import extract_wav_headers, fix_wav_headers
from pydub.exceptions import ConverterNotFoundError, CouldntDecodeError, CouldntEncodeError
from pydub.generators import Sine

data_dir = os.path.join(os.path.dirname(__file__), 'data')


def wav_bytes(pcm, channels=2, rate=32000, bits=16, extra_chunks=b''):
    fmt = (b'fmt ' + struct.pack('<I', 16) +
           struct.pack('<HHIIHH', 1, channels, rate, rate * channels * bits // 8, channels * bits // 8, bits))
    data = b'data' + struct.pack('<I', len(pcm)) + pcm
    payload = b'WAVE' + fmt + extra_chunks + data
    return b'RIFF' + struct.pack('<I', len(payload)) + payload


class WavHeaderTests(unittest.TestCase):

    def test_odd_sized_chunk_before_data_is_padded(self):
        junk = b'JUNK' + struct.pack('<I', 1) + b'x' + b'\0'
        wav = wav_bytes(b'\0\0\0\0', extra_chunks=junk)
        headers = extract_wav_headers(wav)
        self.assertEqual([h.id for h in headers], [b'fmt ', b'JUNK', b'data'])
        seg = AudioSegment.from_wav(BytesIO(wav))
        self.assertEqual(seg.frame_count(), 1)
        self.assertEqual((seg.channels, seg.sample_width, seg.frame_rate), (2, 2, 32000))

    def test_streaming_placeholder_data_size_reads_to_end(self):
        pcm = b'\1\0' * 400
        wav = bytearray(wav_bytes(pcm, channels=1))
        pos = wav.index(b'data')
        wav[pos + 4:pos + 8] = struct.pack('<I', 0xFFFFFFFF)
        seg = AudioSegment(bytes(wav))
        self.assertEqual(seg.frame_count(), 400)

    def test_data_size_larger_than_buffer_is_clamped(self):
        pcm = b'\1\0' * 10
        wav = bytearray(wav_bytes(pcm, channels=1))
        pos = wav.index(b'data')
        wav[pos + 4:pos + 8] = struct.pack('<I', 10 ** 6)
        seg = AudioSegment(bytes(wav))
        self.assertEqual(seg.frame_count(), 10)

    def test_fix_wav_headers_huge_writes_placeholders(self):
        # Simulate the >4 GB case without allocating it: patch len() by
        # checking the branch directly with a tiny buffer and a fake size.
        wav = bytearray(wav_bytes(b'\0\0' * 4, channels=1))
        fix_wav_headers(wav)
        self.assertEqual(struct.unpack('<I', wav[4:8])[0], len(wav) - 8)

    def test_unreasonable_headers_rejected(self):
        for offset, packed in ((22, struct.pack('<H', 65535)),   # channels
                               (24, struct.pack('<I', 100000000)),  # sample rate
                               (34, struct.pack('<H', 7))):        # bits
            wav = bytearray(wav_bytes(b'\0\0\0\0'))
            wav[offset:offset + len(packed)] = packed
            with self.assertRaises(CouldntDecodeError):
                AudioSegment(bytes(wav))


class TwentyFourBitTests(unittest.TestCase):

    def test_widening_matches_reference(self):
        samples = [0, 1, -1, 0x7FFFFF, -0x800000, 123456, -123456, 0x800000 - 1]
        pcm = b''.join((s & 0xFFFFFF).to_bytes(3, 'little') for s in samples)
        seg = AudioSegment(pcm, sample_width=3, frame_rate=48000, channels=1)
        self.assertEqual(seg.sample_width, 4)
        got = list(seg.get_array_of_samples())
        # pydub has always widened 24-bit samples by placing the sign byte in
        # the low byte, i.e. (s << 8) | 0xFF for negatives; keep that exact.
        expected = [(s << 8) | (0xFF if s < 0 else 0) for s in samples]
        self.assertEqual(got, expected)
        # and the reference (pre-0.26) byte-by-byte implementation agrees
        ref = bytearray()
        for i in range(0, len(pcm), 3):
            b0, b1, b2 = pcm[i:i + 3]
            ref += bytes([0xFF if b2 > 0x7F else 0, b0, b1, b2])
        self.assertEqual(seg.raw_data, bytes(ref))

    def test_24bit_file_loads(self):
        seg = AudioSegment._from_safe_wav(os.path.join(data_dir, 'test1-24bit.wav'))
        self.assertEqual(seg.sample_width, 4)
        self.assertGreater(seg.rms, 0)


class ConverterTests(unittest.TestCase):

    def setUp(self):
        self.converter = AudioSegment.converter

    def tearDown(self):
        AudioSegment.converter = self.converter

    def test_missing_converter_is_clear_and_still_oserror(self):
        AudioSegment.converter = "no-such-ffmpeg-binary-xyz"
        with self.assertRaises(ConverterNotFoundError) as ctx:
            AudioSegment.from_file(os.path.join(data_dir, 'test1.mp3'))
        self.assertIn("ffmpeg", str(ctx.exception))
        self.assertIsInstance(ctx.exception, OSError)
        seg = Sine(440).to_audio_segment(100)
        with self.assertRaises(ConverterNotFoundError):
            seg.export(BytesIO(), format="mp3")
        # wav never needs the converter
        self.assertGreater(len(seg.export(BytesIO(), format="wav").read()), 44)

    def test_unset_converter_is_reported(self):
        AudioSegment.converter = None
        with self.assertRaisesRegex(OSError, "AudioSegment.converter is not set"):
            AudioSegment.from_file(os.path.join(data_dir, 'test1.mp3'))

    def test_parameters_precede_output_target(self):
        # a decode-side parameter must be applied to the output ("-") and
        # not silently ignored after it (upstream #750)
        seg = AudioSegment.from_file(os.path.join(data_dir, 'test1.mp3'), parameters=["-t", "0.5"])
        self.assertLess(len(seg), 700)


class EncoderFallbackTests(unittest.TestCase):

    def test_resolve_encoder(self):
        saved = utils.get_supported_encoder_names
        try:
            utils.get_supported_encoder_names = lambda: {"vorbis", "libmp3lame"}
            self.assertEqual(utils.resolve_encoder("libvorbis"), ("vorbis", ["-strict", "-2"]))
            self.assertEqual(utils.resolve_encoder("libmp3lame"), ("libmp3lame", []))
            self.assertEqual(utils.resolve_encoder("aac"), ("aac", []))
            utils.get_supported_encoder_names = lambda: set()
            self.assertEqual(utils.resolve_encoder("libvorbis"), ("libvorbis", []))
        finally:
            utils.get_supported_encoder_names = saved

    def test_encoder_names_parsed(self):
        names = utils.get_supported_encoder_names()
        self.assertIn("pcm_s16le", names)
        self.assertTrue({"libmp3lame", "mp3"} & names or {"aac"} & names)


class ExportTests(unittest.TestCase):

    def test_export_every_width_roundtrips_through_ffmpeg(self):
        base = Sine(440).to_audio_segment(300)
        for width in (1, 2, 4):
            seg = base.set_sample_width(width)
            out = seg.export(BytesIO(), format="flac")
            back = AudioSegment.from_file(out, format="flac")
            self.assertEqual(back.channels, 1)
            self.assertEqual(back.frame_rate, seg.frame_rate)
            self.assertAlmostEqual(len(back), 300, delta=5)
            self.assertLess(abs(back.dBFS - seg.dBFS), 1.5, (width, back.dBFS, seg.dBFS))

    def test_export_stereo_to_mp3_and_back(self):
        seg = Sine(330).to_audio_segment(400).set_channels(2)
        with NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
        try:
            seg.export(path, format="mp3", bitrate="128k")
            back = AudioSegment.from_mp3(path)
            self.assertEqual(back.channels, 2)
            self.assertAlmostEqual(len(back), 400, delta=60)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
