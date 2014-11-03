"""
Each generator will return float samples from -1.0 to 1.0, which can be converted
to actual audio with 8, 16, 24, or 32 bit depth using the AudioSegment.from_generator
class method.
"""

import math
import array
import itertools
from pydub.audio_segment import AudioSegment
from pydub.utils import db_to_float



FRAME_WIDTHS = {
	8: 1,
	16: 2,
	32: 4,
}
ARRAY_TYPES = {
	8:  "b",
	16: "h",
	32: "i",
}
ARRAY_RANGES = {
	8: (-0x80, 0x7f),
	16: (-0x8000, 0x7fff),
	32: (-0x80000000, 0x7fffffff),
}



class SignalGenerator(object):
	def __init__(self, sample_rate=44100, bit_depth=16):
		self.sample_rate = sample_rate
		self.bit_depth = bit_depth

	def to_audio_segment(self, duration=1.0, volume=0.0):
		"""
		Duration in seconds
			(default: 1 second)
		Volume in DB relative to maximum amplitude
			(default 0.0 dBFS, which is the maximum value)
		"""
		minval, maxval = ARRAY_RANGES[self.bit_depth]
		sample_width = FRAME_WIDTHS[self.bit_depth]
		array_type = ARRAY_TYPES[self.bit_depth]
		
		gain = db_to_float(volume)
		sample_count = self.sample_rate * duration

		sample_data = (int(val * maxval * gain) for val in self.generate())
		sample_data = itertools.islice(sample_data, 0, sample_count)

		data = array.array(array_type, sample_data)
		
		return AudioSegment(data=data.tostring(), metadata={
			"channels": 1,
			"sample_width": sample_width,
			"frame_rate": self.sample_rate,
			"frame_width": sample_width,
		})

		

class Sine(SignalGenerator):
	def __init__(self, freq, *args, **kwargs):
		super(Sine, self).__init__(*args, **kwargs)
		self.freq = freq

	def generate(self):
		"""
		freq in Hz
		sample_rate in samples/sec
		"""
		sample_n = 0
		while True:
			sine_of = (self.freq * 2 * math.pi) / self.sample_rate
			yield math.sin(sine_of * sample_n)
			sample_n += 1
	