"""This module provides scipy versions of high_pass_filter and low_pass_filter
as well as an additional band_pass_filter.

Of course, you will need to install scipy for these to work.

When this module is imported the high and low pass filters from this module
will be used when calling audio_segment.high_pass_filter() and
audio_segment.high_pass_filter() instead of the slower, less powerful versions
provided by pydub.effects.
"""

from scipy.signal import butter, sosfilt
from .utils import register_pydub_effect


def _mk_butter_filter(freq, type, order=5):
    """Create a butterworth filter with the given cutoff frequency,
    type, and order.

    Parameters
    ----------
    freq : float or list
        The cutoff frequency for high-pass and low-pass filters.
        For band-pass filters, a list of [low_cutoff, high_cutoff].
    type : string
        "lowpass", "highpass", or "bandpass"
    order : int, optional
        Default = 5
        The order of the butterworth filter.
        The attenuation is -6 dB/octave beyond the cutoff frequency for a
        1st order filter. A Higher order filter will have more attenuation,
        each level adding an additional -6 dB (e.g. a 3rd order butterworth
        filter would have an attenuation of -18 dB/octave).

    Returns
    -------
    function
        A function which can filter a mono audio segment.
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
    filter_fn = _mk_butter_filter([low_cutoff_freq, high_cutoff_freq], 'bandpass', order=order)
    return seg.apply_mono_filter_to_each_channel(filter_fn)


@register_pydub_effect
def high_pass_filter(seg, cutoff_freq, order=5):
    filter_fn = _mk_butter_filter(cutoff_freq, 'highpass', order=order)
    return seg.apply_mono_filter_to_each_channel(filter_fn)


@register_pydub_effect
def low_pass_filter(seg, cutoff_freq, order=5):
    filter_fn = _mk_butter_filter(cutoff_freq, 'lowpass', order=order)
    return seg.apply_mono_filter_to_each_channel(filter_fn)
