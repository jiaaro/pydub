"""
Support for playing AudioSegments. Pyaudio will be used if it's installed,
otherwise will fallback to ffplay. Pyaudio is a *much* nicer solution, but
is tricky to install. See my notes on installing pyaudio in a virtualenv (on 
OSX 10.10): https://gist.github.com/jiaaro/9767512210a1d80a8a0d
"""

import subprocess
from tempfile import NamedTemporaryFile
from .utils import get_player_name, make_chunks

PLAYER = get_player_name()



def _play_with_ffplay(seg):
	with NamedTemporaryFile("w+b", suffix=".wav") as f:
		seg.export(f.name, "wav")
		subprocess.call([PLAYER, "-nodisp", "-autoexit", f.name])


def _play_with_pyaudio(seg):
	import pyaudio

	p = pyaudio.PyAudio()
	stream = p.open(format=p.get_format_from_width(seg.sample_width),  
                	channels=seg.channels,
	                rate=seg.frame_rate,
    	            output=True)

	# break audio into half-second chunks (to allows keyboard interrupts)
	for chunk in make_chunks(seg, 500):
		stream.write(chunk._data)

	stream.stop_stream()  
	stream.close()  

	p.terminate()  


def play(audio_segment):
	try:
		import pyaudio
		_play_with_pyaudio(audio_segment)
	except ImportError:
		_play_with_ffplay(audio_segment)
	    
