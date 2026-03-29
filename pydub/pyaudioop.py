# Py3 compatibility: 'buffer' builtin removed; alias for bytes
try:
    buffer  # type: ignore[name-defined]
except NameError:  # pragma: no cover

    def buffer(b):  # type: ignore[func-returns-value]
        return b


try:
    from __builtin__ import max as builtin_max, min as builtin_min  # type: ignore
except ImportError:
    from builtins import max as builtin_max, min as builtin_min

import math
import struct

try:
    from fractions import gcd  # type: ignore
except ImportError:  # Python 3.9+
    from math import gcd
from ctypes import create_string_buffer


class error(Exception):
    pass


def _check_size(size: int) -> None:
    if size not in (1, 2, 4):
        raise error("Size should be 1, 2 or 4")


def _check_params(length: int, size: int) -> None:
    _check_size(size)
    if length % size != 0:
        raise error("not a whole number of frames")


def _sample_count(cp: bytes, size: int) -> int:
    # Python 3: ensure integer division
    return len(cp) // int(size)


def _struct_format(size: int, signed: bool) -> str:
    # Native-endian, standard sizes (matches typical audioop behavior on little-endian)
    if size == 1:
        return "b" if signed else "B"
    if size == 2:
        return "h" if signed else "H"
    if size == 4:
        return "i" if signed else "I"
    raise error("Size should be 1, 2 or 4")


def _get_sample(cp: bytes, size: int, i: int, signed: bool = True) -> int:
    fmt = _struct_format(size, signed)
    start = i * size
    end = start + size
    return struct.unpack_from(fmt, buffer(cp)[start:end])[0]


def _put_sample(cp, size: int, i: int, val: int, signed: bool = True) -> None:
    fmt = _struct_format(size, signed)
    struct.pack_into(fmt, cp, i * size, val)


def _get_maxval(size: int, signed: bool = True) -> int:
    if size == 1:
        return 0x7F if signed else 0xFF
    if size == 2:
        return 0x7FFF if signed else 0xFFFF
    if size == 4:
        return 0x7FFFFFFF if signed else 0xFFFFFFFF
    raise error("Size should be 1, 2 or 4")


def _get_minval(size: int, signed: bool = True) -> int:
    if not signed:
        return 0
    if size == 1:
        return -0x80
    if size == 2:
        return -0x8000
    if size == 4:
        return -0x80000000
    raise error("Size should be 1, 2 or 4")


def _get_clipfn(size: int, signed: bool = True):
    maxval = _get_maxval(size, signed)
    minval = _get_minval(size, signed)
    return lambda val: builtin_max(min(val, maxval), minval)


def _overflow(val: int, size: int, signed: bool = True) -> int:
    minval = _get_minval(size, signed)
    maxval = _get_maxval(size, signed)
    if minval <= val <= maxval:
        return val

    bits = size * 8
    if signed:
        offset = 2 ** (bits - 1)
        return ((val + offset) % (2**bits)) - offset
    else:
        return val % (2**bits)


def _get_samples(cp: bytes, size: int, signed: bool = True):
    for i in range(_sample_count(cp, size)):
        yield _get_sample(cp, size, i, signed)


def getsample(cp: bytes, size: int, i: int) -> int:
    _check_params(len(cp), size)
    if not (0 <= i < (len(cp) // size)):
        raise error("Index out of range")
    return _get_sample(cp, size, i)


def max(cp: bytes, size: int) -> int:
    _check_params(len(cp), size)
    if len(cp) == 0:
        return 0
    return builtin_max(abs(sample) for sample in _get_samples(cp, size))


def minmax(cp: bytes, size: int):
    _check_params(len(cp), size)
    max_sample, min_sample = 0, 0
    for sample in _get_samples(cp, size):
        max_sample = builtin_max(sample, max_sample)
        min_sample = builtin_min(sample, min_sample)
    return min_sample, max_sample


def avg(cp: bytes, size: int):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count == 0:
        return 0
    return sum(_get_samples(cp, size)) / sample_count


def rms(cp: bytes, size: int) -> int:
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count == 0:
        return 0
    sum_squares = sum(sample**2 for sample in _get_samples(cp, size))
    return int(math.sqrt(sum_squares / sample_count))


def _sum2(cp1: bytes, cp2: bytes, length: int) -> int:
    size = 2
    total = 0
    for i in range(length):
        total += getsample(cp1, size, i) * getsample(cp2, size, i)
    return total


def findfit(cp1: bytes, cp2: bytes):
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

        sum_aij_2 += aj_lm1**2 - aj_m1**2
        sum_aij_ri = _sum2(buffer(cp1)[i * size :], cp2, len2)

        result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

        if result < best_result:
            best_result = result
            best_i = i

    factor = _sum2(buffer(cp1)[best_i * size :], cp2, len2) / sum_ri_2
    return best_i, factor


def findfactor(cp1: bytes, cp2: bytes):
    size = 2

    if len(cp1) % 2 != 0:
        raise error("Strings should be even-sized")
    if len(cp1) != len(cp2):
        raise error("Samples should be same size")

    sample_count = _sample_count(cp1, size)
    sum_ri_2 = _sum2(cp2, cp2, sample_count)
    sum_aij_ri = _sum2(cp1, cp2, sample_count)
    return sum_aij_ri / sum_ri_2


def findmax(cp: bytes, len2: int) -> int:
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
        sample_leaving_window = getsample(cp, size, i - 1)
        sample_entering_window = getsample(cp, size, i + len2 - 1)
        result -= sample_leaving_window**2
        result += sample_entering_window**2
        if result > best_result:
            best_result = result
            best_i = i

    return best_i


def avgpp(cp: bytes, size: int):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    prevextremevalid = False
    prevextreme = None
    avg = 0
    nextreme = 0

    prevval = getsample(cp, size, 0)
    val = getsample(cp, size, 1)
    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = getsample(cp, size, i)
        diff = val - prevval

        if diff * prevdiff < 0:
            if prevextremevalid:
                avg += abs(prevval - prevextreme)  # type: ignore[operator]
                nextreme += 1
            prevextremevalid = True
            prevextreme = prevval

        prevval = val
        if diff != 0:
            prevdiff = diff

    if nextreme == 0:
        return 0
    return avg / nextreme


def maxpp(cp: bytes, size: int):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    prevextremevalid = False
    prevextreme = None
    max_val = 0  # avoid shadowing builtin

    prevval = getsample(cp, size, 0)
    val = getsample(cp, size, 1)
    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = getsample(cp, size, i)
        diff = val - prevval

        if diff * prevdiff < 0:
            if prevextremevalid:
                extremediff = abs(prevval - prevextreme)  # type: ignore[operator]
                if extremediff > max_val:
                    max_val = extremediff
            prevextremevalid = True
            prevextreme = prevval

        prevval = val
        if diff != 0:
            prevdiff = diff

    return max_val


def cross(cp: bytes, size: int) -> int:
    _check_params(len(cp), size)
    crossings = 0
    last_sample = 0
    for sample in _get_samples(cp, size):
        if (sample <= 0 < last_sample) or (sample >= 0 > last_sample):
            crossings += 1
        last_sample = sample
    return crossings


def mul(cp: bytes, size: int, factor: float) -> bytes:
    _check_params(len(cp), size)
    clip = _get_clipfn(size)

    result = create_string_buffer(len(cp))
    for i, sample in enumerate(_get_samples(cp, size)):
        sample = clip(int(sample * factor))
        _put_sample(result, size, i, sample)
    return result.raw


def tomono(cp: bytes, size: int, fac1: float, fac2: float) -> bytes:
    _check_params(len(cp), size)
    clip = _get_clipfn(size)

    sample_count = _sample_count(cp, size)
    result = create_string_buffer(len(cp) // 2)

    for i in range(0, sample_count, 2):
        l_sample = getsample(cp, size, i)
        r_sample = getsample(cp, size, i + 1)
        sample = clip(int(l_sample * fac1 + r_sample * fac2))
        _put_sample(result, size, i // 2, sample)

    return result.raw


def tostereo(cp: bytes, size: int, fac1: float, fac2: float) -> bytes:
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    result = create_string_buffer(len(cp) * 2)
    clip = _get_clipfn(size)

    for i in range(sample_count):
        sample = _get_sample(cp, size, i)
        l_sample = clip(int(sample * fac1))
        r_sample = clip(int(sample * fac2))
        _put_sample(result, size, i * 2, l_sample)
        _put_sample(result, size, i * 2 + 1, r_sample)

    return result.raw


def add(cp1: bytes, cp2: bytes, size: int) -> bytes:
    _check_params(len(cp1), size)
    if len(cp1) != len(cp2):
        raise error("Lengths should be the same")

    clip = _get_clipfn(size)
    sample_count = _sample_count(cp1, size)
    result = create_string_buffer(len(cp1))

    for i in range(sample_count):
        sample1 = getsample(cp1, size, i)
        sample2 = getsample(cp2, size, i)
        _put_sample(result, size, i, clip(sample1 + sample2))

    return result.raw


def bias(cp: bytes, size: int, bias_val: int) -> bytes:
    _check_params(len(cp), size)
    result = create_string_buffer(len(cp))
    for i, sample in enumerate(_get_samples(cp, size)):
        _put_sample(result, size, i, _overflow(sample + bias_val, size))
    return result.raw


def reverse(cp: bytes, size: int) -> bytes:
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    result = create_string_buffer(len(cp))
    for i, sample in enumerate(_get_samples(cp, size)):
        _put_sample(result, size, sample_count - i - 1, sample)
    return result.raw


def lin2lin(cp: bytes, size: int, size2: int) -> bytes:
    _check_params(len(cp), size)
    _check_size(size2)

    if size == size2:
        return cp

    new_len = (len(cp) // size) * size2
    result = create_string_buffer(new_len)

    # shift amounts must be ints
    shift_up = (4 * size2) // size
    shift_down = (4 * size) // size2

    for i in range(_sample_count(cp, size)):
        sample = _get_sample(cp, size, i)
        if size < size2:
            sample = sample << shift_up
        elif size > size2:
            sample = sample >> shift_down
        sample = _overflow(sample, size2)
        _put_sample(result, size2, i, sample)

    return result.raw


def ratecv(
    cp: bytes, size: int, nchannels: int, inrate: int, outrate: int, state, weightA=1, weightB=0
):
    _check_params(len(cp), size)
    if nchannels < 1:
        raise error("# of channels should be >= 1")

    bytes_per_frame = size * nchannels
    frame_count = len(cp) // bytes_per_frame

    if (bytes_per_frame // nchannels) != size:
        raise OverflowError("width * nchannels too big for a C int")
    if weightA < 1 or weightB < 0:
        raise error("weightA should be >= 1, weightB should be >= 0")
    if len(cp) % bytes_per_frame != 0:
        raise error("not a whole number of frames")
    if inrate <= 0 or outrate <= 0:
        raise error("sampling rate not > 0")

    d = gcd(inrate, outrate)
    inrate //= d
    outrate //= d

    prev_i = [0] * nchannels
    cur_i = [0] * nchannels

    if state is None:
        d = -outrate
    else:
        d, samps = state
        if len(samps) != nchannels:
            raise error("illegal state argument")
        prev_i, cur_i = zip(*samps)
        prev_i, cur_i = list(prev_i), list(cur_i)

    q = frame_count // inrate
    ceiling = (q + 1) * outrate
    nbytes = ceiling * bytes_per_frame
    result = create_string_buffer(nbytes)

    samples = _get_samples(cp, size)
    out_i = 0
    while True:
        while d < 0:
            if frame_count == 0:
                samps = zip(prev_i, cur_i)
                retval = result.raw
                # slice off extra bytes
                trim_index = (out_i * bytes_per_frame) - len(retval)
                retval = buffer(retval)[:trim_index]
                return (retval, (d, tuple(samps)))

            for chan in range(nchannels):
                prev_i[chan] = cur_i[chan]
                cur_i[chan] = next(samples)  # Py3
                cur_i[chan] = int(
                    (weightA * cur_i[chan] + weightB * prev_i[chan]) / (weightA + weightB)
                )

            frame_count -= 1
            d += outrate

        while d >= 0:
            for chan in range(nchannels):
                cur_o = (prev_i[chan] * d + cur_i[chan] * (outrate - d)) / outrate
                _put_sample(result, size, out_i, _overflow(int(cur_o), size))
                out_i += 1
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
