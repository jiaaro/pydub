"""
Support for playing AudioSegments. Pyaudio will be used if it's installed,
otherwise will fallback to ffplay. Pyaudio is a *much* nicer solution, but
is tricky to install. See my notes on installing pyaudio in a virtualenv (on
OSX 10.10): https://gist.github.com/jiaaro/9767512210a1d80a8a0d
"""

import subprocess
from tempfile import NamedTemporaryFile
from .utils import get_player_name, make_chunks

def _play_with_ffplay(seg, temp=None, delete=True):
    PLAYER = get_player_name()
    with NamedTemporaryFile("w+b", suffix=".wav", dir=temp, delete=delete) as f:
        seg.export(f.name, "wav")
        subprocess.call([PLAYER, "-nodisp", "-autoexit", "-hide_banner", f.name])


def _play_with_pyaudio(seg):
    import pyaudio

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(seg.sample_width),
                    channels=seg.channels,
                    rate=seg.frame_rate,
                    output=True)

    # Just in case there were any exceptions/interrupts, we release the resource
    # So as not to raise OSError: Device Unavailable should play() be used again
    try:
        # break audio into half-second chunks (to allows keyboard interrupts)
        for chunk in make_chunks(seg, 500):
            stream.write(chunk._data)
    finally:
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


def play(audio_segment, temp=None, delete=True):
    """Plays an audio segment.

    Args:
        audio_segment: The audio segment to play. This could be a pydub
                       AudioSegment object or a path to an audio file.
        temp (str, optional): While using the 'ffmpeg' player.
                              A path to a temporary file where the audio segment
                              will be saved before playing. If None, a default
                              temporary file location will be used. Defaults to None.
        delete (bool, optional): While using the 'ffmpeg' player.
                                 If True, the temporary audio file will be
                                 deleted after playback. Defaults to True.
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
    except ImportError:
        pass
    else:
        return

    _play_with_ffplay(audio_segment, temp, delete)
