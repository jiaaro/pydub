"""
Support for playing AudioSegments. Pyaudio will be used if it's installed,
otherwise will fallback to ffplay. Pyaudio is a *much* nicer solution, but
is tricky to install. See my notes on installing pyaudio in a virtualenv (on
OSX 10.10): https://gist.github.com/jiaaro/9767512210a1d80a8a0d
"""

import subprocess
from tempfile import NamedTemporaryFile
from .utils import get_player_name, make_chunks

def _play_with_ffplay(seg):
    PLAYER = get_player_name()
    with NamedTemporaryFile("w+b", suffix=".wav") as f:
        seg.export(f.name, "wav")
        subprocess.call([PLAYER, "-nodisp", "-autoexit", "-hide_banner", f.name])


def _play_with_pyaudio(seg, output_device=None):
    import pyaudio
    p = pyaudio.PyAudio()

    if output_device is None:
        output_device = p.get_default_output_device_info()["index"]

    elif not isinstance(output_device, int):
        raise TypeError("Output_device must be an integer.")

    stream = p.open(output_device_index=output_device,
                    format=p.get_format_from_width(seg.sample_width),
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


def play(audio_segment, output_device=None):
    """
    Plays the given AudioSegment. Installing pyaudio is highly recommended, as simpleaudio is deprecated. If neither
    are available, ffplay will be used as a last resort.
    :param audio_segment: pydub.AudioSegment
    :param output_device: Only works with pyaudio. If None, the default device will be used. Needs to be an pyaudio
        device index (integer).
    :return: None
    """
    try:
        _play_with_pyaudio(audio_segment, output_device)
    except ImportError:
        pass
    else:
        return
    try:
        playback = _play_with_simpleaudio(audio_segment)
        return
        try:
            playback.wait_done()
        except KeyboardInterrupt:
            playback.stop()
    except ImportError:
        pass
    else:
        return
    print("No suitable audio playback module available. Consider installing pyaudio.")
    _play_with_ffplay(audio_segment)
