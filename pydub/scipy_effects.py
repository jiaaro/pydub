"""
This module provides scipy versions of high_pass_filter, and low_pass_filter
as well as an additional band_pass_filter.

Of course, you will need to install scipy for these to work.

When this module is imported the high and low pass filters from this module
will be used when calling audio_segment.high_pass_filter() and
audio_segment.high_pass_filter() instead of the slower, less powerful versions
provided by pydub.effects.
"""
from scipy.signal import butter, sosfilt
from .utils import register_pydub_effect


def _mk_butter_filter(freq, type, order):
    """
    Args:
        freq: The cutoff frequency for highpass and lowpass filters. For
            band filters, a list of [low_cutoff, high_cutoff]
        type: "lowpass", "highpass", or "band"
        order: nth order butterworth filter (default: 5th order). The
            attenuation is -6dB/octave beyond the cutoff frequency (for 1st
            order). A Higher order filter will have more attenuation, each level
            adding an additional -6dB (so a 3rd order butterworth filter would
            be -18dB/octave).

    Returns:
        function which can filter a mono audio segment

    """
    def filter_fn(seg):
        assert seg.channels == 1

        nyq = 0.5 * seg.frame_rate
        try:
            freqs = [f / nyq for f in freq]
        except TypeError:
            freqs = freq / nyq

        sos = butter(order, freqs, btype=type, output='sos')
        y = sosfilt(sos, seg.get_array_of_samples())

        return seg._spawn(y.astype(seg.array_type))

    return filter_fn


@register_pydub_effect
def band_pass_filter(seg, low_cutoff_freq, high_cutoff_freq, order=5):
    filter_fn = _mk_butter_filter([low_cutoff_freq, high_cutoff_freq], 'band', order=order)
    return seg.apply_mono_filter_to_each_channel(filter_fn)


@register_pydub_effect
def high_pass_filter(seg, cutoff_freq, order=5):
    filter_fn = _mk_butter_filter(cutoff_freq, 'highpass', order=order)
    return seg.apply_mono_filter_to_each_channel(filter_fn)


@register_pydub_effect
def low_pass_filter(seg, cutoff_freq, order=5):
    filter_fn = _mk_butter_filter(cutoff_freq, 'lowpass', order=order)
    return seg.apply_mono_filter_to_each_channel(filter_fn)
