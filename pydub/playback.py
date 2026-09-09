"""
Support for playing AudioSegments. Pyaudio will be used if it's installed,
otherwise will fallback to ffplay. Pyaudio is a *much* nicer solution, but
is tricky to install. See my notes on installing pyaudio in a virtualenv (on
OSX 10.10): https://gist.github.com/jiaaro/9767512210a1d80a8a0d
"""

import os
import subprocess
from tempfile import NamedTemporaryFile
from .utils import get_player_name, make_chunks, missing_converter_message

def _play_with_ffplay(seg):
    PLAYER = get_player_name()
    # Close the temp file before ffplay opens it: on Windows a file that is
    # still open in this process can't be read by another one.
    f = NamedTemporaryFile("w+b", suffix=".wav", delete=False)
    f.close()
    try:
        seg.export(f.name, "wav")
        try:
            subprocess.call([PLAYER, "-nodisp", "-autoexit", "-hide_banner",
                             "-loglevel", "error", f.name])
        except FileNotFoundError:
            raise OSError(missing_converter_message(PLAYER))
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass


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


def play(audio_segment):
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

    _play_with_ffplay(audio_segment)
