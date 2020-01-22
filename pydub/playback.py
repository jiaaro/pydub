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



def _play_with_ffplay(seg, quiet):
    with NamedTemporaryFile("w+b", suffix=".wav") as f:
        seg.export(f.name, "wav")
        if not quiet:
            subprocess.call([PLAYER, "-nodisp", "-autoexit", "-hide_banner", f.name])
        else:
            subprocess.call([PLAYER, "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "quiet", f.name])


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


def _play_with_simpleaudio(seg):
    import simpleaudio
    return simpleaudio.play_buffer(
        seg.raw_data, 
        num_channels=seg.channels, 
        bytes_per_sample=seg.sample_width, 
        sample_rate=seg.frame_rate
    )


def play(audio_segment, quiet=False):
    """
    Plays the audio within audio_segment

    audio_segment: The audio container
    quiet: Flag to suppress output while playing(only while using ffplay), Defaults to False

    audio_segment: pydub.audio_segment.AudioSegment
    quiet: Boolean
    """
    try:
        playback = _play_with_simpleaudio(audio_segment)
        try:
            playback.wait_done()
        except KeyboardInterrupt:
            playback.stop()
    except ImportError:
        pass
    else:
        return
    
    try:
        _play_with_pyaudio(audio_segment)
        return
    except ImportError:
        pass
    else:
        return
    
    _play_with_ffplay(audio_segment, quiet)
