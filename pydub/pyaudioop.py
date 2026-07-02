"""Pure-Python reimplementation of the parts of the stdlib ``audioop`` module
that pydub relies on.

``audioop`` was deprecated in Python 3.11 and removed in Python 3.13.  pydub
falls back to ``from . import pyaudioop as audioop`` when the C module is
missing, so this module provides a dependency-free replacement for the
functions pydub uses:

    add, avg, bias, lin2lin, max, mul, ratecv, reverse, rms, tomono, tostereo

plus the other analysis helpers historically exposed by audioop.

Fragments are byte strings of signed little-endian integers with a sample
width (``size``) of 1, 2, 3 or 4 bytes, matching the semantics of the original
C module.  The ADPCM/u-law/a-law codecs are not implemented.
"""

import math
import struct

try:
    from math import gcd
except ImportError:  # pragma: no cover - Python < 3.5
    from fractions import gcd

builtin_max = max
builtin_min = min


class error(Exception):
    pass


def _check_size(size):
    if size not in (1, 2, 3, 4):
        raise error("Size should be 1, 2, 3 or 4")


def _check_params(length, size):
    _check_size(size)
    if length % size != 0:
        raise error("not a whole number of frames")


def _sample_count(cp, size):
    return len(cp) // size


def _get_sample(cp, size, i):
    start = i * size
    if size == 1:
        return struct.unpack_from("b", cp, start)[0]
    elif size == 2:
        return struct.unpack_from("<h", cp, start)[0]
    elif size == 3:
        b0, b1, b2 = cp[start], cp[start + 1], cp[start + 2]
        val = b0 | (b1 << 8) | (b2 << 16)
        if val & 0x800000:
            val -= 0x1000000
        return val
    elif size == 4:
        return struct.unpack_from("<i", cp, start)[0]


def _get_samples(cp, size):
    for i in range(_sample_count(cp, size)):
        yield _get_sample(cp, size, i)


def _pack_sample(val, size):
    val = int(val)
    if size == 1:
        return struct.pack("b", val)
    elif size == 2:
        return struct.pack("<h", val)
    elif size == 3:
        val &= 0xffffff
        return bytes((val & 0xff, (val >> 8) & 0xff, (val >> 16) & 0xff))
    elif size == 4:
        return struct.pack("<i", val)


def _get_maxval(size):
    return (1 << (size * 8 - 1)) - 1


def _get_minval(size):
    return -(1 << (size * 8 - 1))


def _clip(val, size):
    maxval = _get_maxval(size)
    minval = _get_minval(size)
    if val > maxval:
        return maxval
    if val < minval:
        return minval
    return int(val)


def _overflow(val, size):
    """Wrap ``val`` into the signed range for ``size`` (two's complement)."""
    minval = _get_minval(size)
    maxval = _get_maxval(size)
    if minval <= val <= maxval:
        return int(val)
    bits = size * 8
    offset = 1 << (bits - 1)
    return ((int(val) + offset) % (1 << bits)) - offset


def getsample(cp, size, i):
    _check_params(len(cp), size)
    if not (0 <= i < _sample_count(cp, size)):
        raise error("Index out of range")
    return _get_sample(cp, size, i)


def max(cp, size):
    _check_params(len(cp), size)
    if len(cp) == 0:
        return 0
    return builtin_max(abs(sample) for sample in _get_samples(cp, size))


def minmax(cp, size):
    _check_params(len(cp), size)
    max_sample, min_sample = -0x80000000, 0x7fffffff
    for sample in _get_samples(cp, size):
        max_sample = builtin_max(sample, max_sample)
        min_sample = builtin_min(sample, min_sample)
    if len(cp) == 0:
        min_sample, max_sample = 0x7fffffff, -0x80000000
    return min_sample, max_sample


def avg(cp, size):
    _check_params(len(cp), size)
    count = _sample_count(cp, size)
    if count == 0:
        return 0
    return sum(_get_samples(cp, size)) // count


def rms(cp, size):
    _check_params(len(cp), size)
    count = _sample_count(cp, size)
    if count == 0:
        return 0
    sum_squares = sum(sample * sample for sample in _get_samples(cp, size))
    return int(math.sqrt(sum_squares / count))


def _sum2(cp1, cp2, length):
    size = 2
    total = 0
    for i in range(length):
        total += _get_sample(cp1, size, i) * _get_sample(cp2, size, i)
    return total


def findfit(cp1, cp2):
    size = 2
    if len(cp1) % 2 != 0 or len(cp2) % 2 != 0:
        raise error("Strings should be even-sized")
    if len(cp1) < len(cp2):
        raise error("First sample should be longer")

    len1 = _sample_count(cp1, size)
    len2 = _sample_count(cp2, size)

    sum_ri_2 = _sum2(cp2, cp2, len2)
    sum_aij_2 = _sum2(cp1, cp1, len2)
    sum_aij_ri = _sum2(cp1, cp2, len2)

    result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

    best_result = result
    best_i = 0

    for i in range(1, len1 - len2 + 1):
        aj_m1 = _get_sample(cp1, size, i - 1)
        aj_lm1 = _get_sample(cp1, size, i + len2 - 1)

        sum_aij_2 += aj_lm1 ** 2 - aj_m1 ** 2
        sum_aij_ri = _sum2(cp1[i * size:], cp2, len2)

        result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

        if result < best_result:
            best_result = result
            best_i = i

    factor = _sum2(cp1[best_i * size:], cp2, len2) / sum_ri_2
    return best_i, factor


def findfactor(cp1, cp2):
    size = 2
    if len(cp1) % 2 != 0:
        raise error("Strings should be even-sized")
    if len(cp1) != len(cp2):
        raise error("Samples should be same size")
    sample_count = _sample_count(cp1, size)
    sum_ri_2 = _sum2(cp2, cp2, sample_count)
    sum_aij_ri = _sum2(cp1, cp2, sample_count)
    return sum_aij_ri / sum_ri_2


def findmax(cp, len2):
    size = 2
    sample_count = _sample_count(cp, size)
    if len(cp) % 2 != 0:
        raise error("Strings should be even-sized")
    if len2 < 0 or sample_count < len2:
        raise error("Input sample should be longer")
    if sample_count == 0:
        return 0

    result = _sum2(cp, cp, len2)
    best_result = result
    best_i = 0

    for i in range(1, sample_count - len2 + 1):
        sample_leaving_window = _get_sample(cp, size, i - 1)
        sample_entering_window = _get_sample(cp, size, i + len2 - 1)
        result -= sample_leaving_window ** 2
        result += sample_entering_window ** 2
        if result > best_result:
            best_result = result
            best_i = i
    return best_i


def avgpp(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count <= 2:
        return 0

    prevextremevalid = False
    prevextreme = None
    total = 0
    nextreme = 0

    prevval = _get_sample(cp, size, 0)
    val = _get_sample(cp, size, 1)
    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = _get_sample(cp, size, i)
        diff = val - prevval
        if diff * prevdiff < 0:
            if prevextremevalid:
                total += abs(prevval - prevextreme)
                nextreme += 1
            prevextremevalid = True
            prevextreme = prevval
        prevval = val
        if diff != 0:
            prevdiff = diff

    if nextreme == 0:
        return 0
    return total // nextreme


def maxpp(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count <= 2:
        return 0

    prevextremevalid = False
    prevextreme = None
    result = 0

    prevval = _get_sample(cp, size, 0)
    val = _get_sample(cp, size, 1)
    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = _get_sample(cp, size, i)
        diff = val - prevval
        if diff * prevdiff < 0:
            if prevextremevalid:
                extremediff = abs(prevval - prevextreme)
                if extremediff > result:
                    result = extremediff
            prevextremevalid = True
            prevextreme = prevval
        prevval = val
        if diff != 0:
            prevdiff = diff
    return result


def cross(cp, size):
    _check_params(len(cp), size)
    crossings = 0
    last_sample = 0
    for sample in _get_samples(cp, size):
        if sample <= 0 < last_sample or sample >= 0 > last_sample:
            crossings += 1
        last_sample = sample
    return crossings


def mul(cp, size, factor):
    _check_params(len(cp), size)
    return b"".join(
        _pack_sample(_clip(math.floor(sample * factor), size), size)
        for sample in _get_samples(cp, size)
    )


def tomono(cp, size, fac1, fac2):
    _check_params(len(cp), size)
    out = bytearray()
    for i in range(0, _sample_count(cp, size), 2):
        l_sample = _get_sample(cp, size, i)
        r_sample = _get_sample(cp, size, i + 1)
        sample = _clip(math.floor(l_sample * fac1 + r_sample * fac2), size)
        out += _pack_sample(sample, size)
    return bytes(out)


def tostereo(cp, size, fac1, fac2):
    _check_params(len(cp), size)
    out = bytearray()
    for sample in _get_samples(cp, size):
        out += _pack_sample(_clip(math.floor(sample * fac1), size), size)
        out += _pack_sample(_clip(math.floor(sample * fac2), size), size)
    return bytes(out)


def add(cp1, cp2, size):
    _check_params(len(cp1), size)
    if len(cp1) != len(cp2):
        raise error("Lengths should be the same")
    return b"".join(
        _pack_sample(_clip(a + b, size), size)
        for a, b in zip(_get_samples(cp1, size), _get_samples(cp2, size))
    )


def bias(cp, size, bias):
    _check_params(len(cp), size)
    return b"".join(
        _pack_sample(_overflow(sample + bias, size), size)
        for sample in _get_samples(cp, size)
    )


def reverse(cp, size):
    _check_params(len(cp), size)
    n = _sample_count(cp, size)
    out = bytearray()
    for i in range(n - 1, -1, -1):
        out += _pack_sample(_get_sample(cp, size, i), size)
    return bytes(out)


def lin2lin(cp, size, size2):
    _check_params(len(cp), size)
    _check_size(size2)
    if size == size2:
        return bytes(cp)

    shift = (size2 - size) * 8
    out = bytearray()
    for sample in _get_samples(cp, size):
        if shift > 0:
            sample = sample << shift
        else:
            sample = sample >> (-shift)
        out += _pack_sample(_overflow(sample, size2), size2)
    return bytes(out)


def _trunc(a, b):
    """Integer division truncated toward zero (matches a C ``(int)`` cast)."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


def ratecv(cp, size, nchannels, inrate, outrate, state, weightA=1, weightB=0):
    _check_size(size)
    if nchannels < 1:
        raise error("# of channels should be >= 1")

    bytes_per_frame = size * nchannels
    if weightA < 1 or weightB < 0:
        raise error("weightA should be >= 1, weightB should be >= 0")
    if len(cp) % bytes_per_frame != 0:
        raise error("not a whole number of frames")
    if inrate <= 0 or outrate <= 0:
        raise error("sampling rate not > 0")

    d = gcd(inrate, outrate)
    inrate //= d
    outrate //= d

    # audioop performs the rate conversion on samples normalized to the top of
    # a 32-bit integer, so its state is expressed in that scaled form too.
    scale = 8 * (4 - size)

    prev_i = [0] * nchannels
    cur_i = [0] * nchannels

    if state is None:
        d = -outrate
    else:
        d, samps = state
        if len(samps) != nchannels:
            raise error("illegal state argument")
        prev_i = [p for p, c in samps]
        cur_i = [c for p, c in samps]

    frame_count = len(cp) // bytes_per_frame
    out = bytearray()
    in_i = 0

    while True:
        while d < 0:
            if frame_count == 0:
                samps = tuple(zip(prev_i, cur_i))
                return bytes(out), (d, samps)
            for chan in range(nchannels):
                prev_i[chan] = cur_i[chan]
                cur_i[chan] = _get_sample(cp, size, in_i) << scale
                in_i += 1
                cur_i[chan] = _trunc(
                    weightA * cur_i[chan] + weightB * prev_i[chan],
                    weightA + weightB,
                )
            frame_count -= 1
            d += outrate
        while d >= 0:
            for chan in range(nchannels):
                cur_o = _trunc(
                    prev_i[chan] * d + cur_i[chan] * (outrate - d),
                    outrate,
                )
                out += _pack_sample(_overflow(cur_o >> scale, size), size)
            d -= inrate


def lin2ulaw(cp, size):
    raise NotImplementedError()


def ulaw2lin(cp, size):
    raise NotImplementedError()


def lin2alaw(cp, size):
    raise NotImplementedError()


def alaw2lin(cp, size):
    raise NotImplementedError()


def lin2adpcm(cp, size, state):
    raise NotImplementedError()


def adpcm2lin(cp, size, state):
    raise NotImplementedError()
