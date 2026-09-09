"""
Pure-Python implementation of the ``audioop`` module.

``audioop`` was removed from the standard library in Python 3.13. pydub
prefers a C implementation when one is importable (the stdlib module on
Python <= 3.12, or the ``audioop-lts`` backport on 3.13+) and falls back
to this module otherwise. When NumPy is installed the hot functions are
vectorised; without it plain Python loops are used, which are slow for
long audio but correct.

Results match CPython's ``Modules/audioop.c`` (clamping, flooring, integer
wrap-around and the ``ratecv`` interpolation) so that switching backends
does not change pydub's output. Only the functions pydub and typical
callers need are implemented; the a-law, u-law and ADPCM codecs raise
``NotImplementedError``.
"""

import array
import math
import struct
import sys

try:
    import numpy as _np
except ImportError:  # pragma: no cover - exercised on machines without numpy
    _np = None

# Set to False to force the pure-Python paths (used by the tests).
use_numpy = _np is not None

__all__ = [
    "error", "getsample", "max", "minmax", "avg", "rms", "cross", "mul",
    "tomono", "tostereo", "add", "bias", "reverse", "byteswap", "lin2lin",
    "ratecv", "lin2ulaw", "ulaw2lin", "lin2alaw", "alaw2lin", "lin2adpcm",
    "adpcm2lin",
]

_builtin_max = max
_builtin_min = min


class error(Exception):
    pass


_MAXVALS = {1: 0x7F, 2: 0x7FFF, 3: 0x7FFFFF, 4: 0x7FFFFFFF}
_MINVALS = {1: -0x80, 2: -0x8000, 3: -0x800000, 4: -0x80000000}
_MASKS = {1: 0xFF, 2: 0xFFFF, 3: 0xFFFFFF, 4: 0xFFFFFFFF}

# array typecodes with the right item sizes on this platform
_TYPECODES = {}
for _code in "bhilq":
    _size = array.array(_code).itemsize
    _TYPECODES.setdefault(_size, _code)
_TYPECODES = {1: _TYPECODES[1], 2: _TYPECODES[2], 4: _TYPECODES[4]}

_LITTLE = sys.byteorder == "little"


def _check_size(size):
    if size not in (1, 2, 3, 4):
        raise error("Size should be 1, 2, 3 or 4")


def _check_params(length, size):
    _check_size(size)
    if length % size != 0:
        raise error("not a whole number of frames")


def _as_bytes(cp):
    if isinstance(cp, (bytes, bytearray)):
        return cp
    return bytes(memoryview(cp))


# ---------------------------------------------------------------- decoding

def _samples_py(cp, size):
    """Signed native-order samples as a Python list."""
    cp = _as_bytes(cp)
    if size == 3:
        out = []
        for i in range(0, len(cp), 3):
            out.append(int.from_bytes(cp[i:i + 3], sys.byteorder, signed=True))
        return out
    a = array.array(_TYPECODES[size])
    a.frombytes(cp)
    return a.tolist()


def _pack_py(samples, size):
    """Signed samples (already in range) to native-order bytes."""
    if size == 3:
        out = bytearray()
        for s in samples:
            out += (s & 0xFFFFFF).to_bytes(3, sys.byteorder)
        return bytes(out)
    a = array.array(_TYPECODES[size], samples)
    return a.tobytes()


def _np_dtype(size):
    return {1: _np.int8, 2: _np.int16, 4: _np.int32}[size]


def _samples_np(cp, size):
    """Signed samples as an int64 numpy array."""
    buf = _np.frombuffer(_as_bytes(cp), dtype=_np.uint8)
    if size == 3:
        b = buf.reshape(-1, 3).astype(_np.int64)
        if _LITTLE:
            v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        else:
            v = b[:, 2] | (b[:, 1] << 8) | (b[:, 0] << 16)
        return _np.where(v & 0x800000, v - 0x1000000, v)
    return buf.view(_np_dtype(size)).astype(_np.int64)


def _pack_np(samples, size):
    """int64 numpy samples (already in range) to native-order bytes."""
    if size == 3:
        v = samples.astype(_np.int64) & 0xFFFFFF
        out = _np.empty((len(v), 3), dtype=_np.uint8)
        if _LITTLE:
            out[:, 0] = v & 0xFF
            out[:, 1] = (v >> 8) & 0xFF
            out[:, 2] = (v >> 16) & 0xFF
        else:
            out[:, 2] = v & 0xFF
            out[:, 1] = (v >> 8) & 0xFF
            out[:, 0] = (v >> 16) & 0xFF
        return out.tobytes()
    return samples.astype(_np_dtype(size)).tobytes()


def _fbound_py(val, size):
    """CPython's fbound(): clamp, then floor, as an int."""
    maxval = _MAXVALS[size]
    minval = _MINVALS[size]
    if val > maxval:
        val = maxval
    elif val < minval + 1.0:
        val = minval
    return int(math.floor(val))


def _fbound_np(vals, size):
    maxval = float(_MAXVALS[size])
    minval = float(_MINVALS[size])
    vals = _np.where(vals > maxval, maxval, vals)
    vals = _np.where(vals < minval + 1.0, minval, vals)
    return _np.floor(vals).astype(_np.int64)


def _np_ok():
    return use_numpy and _np is not None


# ---------------------------------------------------------------- queries

def getsample(cp, size, i):
    _check_params(len(cp), size)
    if not (0 <= i < len(cp) // size):
        raise error("Index out of range")
    cp = _as_bytes(cp)
    return int.from_bytes(cp[i * size:(i + 1) * size], sys.byteorder, signed=True)


def max(cp, size):
    _check_params(len(cp), size)
    if len(cp) == 0:
        return 0
    if _np_ok():
        return int(_np.abs(_samples_np(cp, size)).max())
    return _builtin_max(abs(s) for s in _samples_py(cp, size))


def minmax(cp, size):
    _check_params(len(cp), size)
    if len(cp) == 0:
        return 0x7FFFFFFF, -0x80000000
    if _np_ok():
        s = _samples_np(cp, size)
        return int(s.min()), int(s.max())
    s = _samples_py(cp, size)
    return _builtin_min(s), _builtin_max(s)


def avg(cp, size):
    _check_params(len(cp), size)
    n = len(cp) // size
    if n == 0:
        return 0
    if _np_ok():
        total = float(_samples_np(cp, size).sum(dtype=_np.float64))
    else:
        total = float(sum(_samples_py(cp, size)))
    return int(math.floor(total / n))


def rms(cp, size):
    _check_params(len(cp), size)
    n = len(cp) // size
    if n == 0:
        return 0
    if _np_ok():
        s = _samples_np(cp, size).astype(_np.float64)
        sum_squares = float((s * s).sum())
    else:
        sum_squares = 0.0
        for s in _samples_py(cp, size):
            v = float(s)
            sum_squares += v * v
    return int(math.sqrt(sum_squares / n))


def cross(cp, size):
    _check_params(len(cp), size)
    samples = _samples_py(cp, size) if not _np_ok() else _samples_np(cp, size).tolist()
    ncross = -1
    prevval = 17
    for s in samples:
        val = 1 if s < 0 else 0
        if val != prevval:
            ncross += 1
        prevval = val
    return ncross


# ---------------------------------------------------------------- transforms

def mul(cp, size, factor):
    _check_params(len(cp), size)
    factor = float(factor)
    if _np_ok():
        vals = _samples_np(cp, size).astype(_np.float64) * factor
        return _pack_np(_fbound_np(vals, size), size)
    return _pack_py([_fbound_py(s * factor, size) for s in _samples_py(cp, size)], size)


def tomono(cp, size, fac1, fac2):
    _check_params(len(cp), size)
    if (len(cp) // size) % 2 != 0:
        raise error("not a whole number of frames")
    fac1 = float(fac1)
    fac2 = float(fac2)
    if _np_ok():
        s = _samples_np(cp, size).astype(_np.float64)
        vals = s[0::2] * fac1 + s[1::2] * fac2
        return _pack_np(_fbound_np(vals, size), size)
    s = _samples_py(cp, size)
    out = [_fbound_py(s[i] * fac1 + s[i + 1] * fac2, size) for i in range(0, len(s), 2)]
    return _pack_py(out, size)


def tostereo(cp, size, fac1, fac2):
    _check_params(len(cp), size)
    fac1 = float(fac1)
    fac2 = float(fac2)
    if _np_ok():
        s = _samples_np(cp, size).astype(_np.float64)
        out = _np.empty(len(s) * 2, dtype=_np.int64)
        out[0::2] = _fbound_np(s * fac1, size)
        out[1::2] = _fbound_np(s * fac2, size)
        return _pack_np(out, size)
    out = []
    for s in _samples_py(cp, size):
        out.append(_fbound_py(s * fac1, size))
        out.append(_fbound_py(s * fac2, size))
    return _pack_py(out, size)


def add(cp1, cp2, size):
    _check_params(len(cp1), size)
    if len(cp1) != len(cp2):
        raise error("Lengths should be the same")
    maxval = _MAXVALS[size]
    minval = _MINVALS[size]
    if _np_ok():
        vals = _samples_np(cp1, size) + _samples_np(cp2, size)
        return _pack_np(_np.clip(vals, minval, maxval), size)
    out = []
    for a, b in zip(_samples_py(cp1, size), _samples_py(cp2, size)):
        v = a + b
        if v > maxval:
            v = maxval
        elif v < minval:
            v = minval
        out.append(v)
    return _pack_py(out, size)


def bias(cp, size, bias):
    _check_params(len(cp), size)
    mask = _MASKS[size]
    half = 1 << (size * 8 - 1)
    if _np_ok():
        vals = (_samples_np(cp, size) + int(bias)) & mask
        vals = _np.where(vals >= half, vals - (mask + 1), vals)
        return _pack_np(vals, size)
    out = []
    for s in _samples_py(cp, size):
        v = (s + bias) & mask
        if v >= half:
            v -= mask + 1
        out.append(v)
    return _pack_py(out, size)


def reverse(cp, size):
    _check_params(len(cp), size)
    if _np_ok():
        return _pack_np(_samples_np(cp, size)[::-1], size)
    return _pack_py(_samples_py(cp, size)[::-1], size)


def byteswap(cp, size):
    _check_params(len(cp), size)
    cp = _as_bytes(cp)
    if _np_ok():
        buf = _np.frombuffer(cp, dtype=_np.uint8).reshape(-1, size)
        return buf[:, ::-1].tobytes()
    out = bytearray(len(cp))
    for i in range(0, len(cp), size):
        out[i:i + size] = cp[i:i + size][::-1]
    return bytes(out)


def lin2lin(cp, size, size2):
    _check_params(len(cp), size)
    _check_size(size2)
    if size == size2:
        return _as_bytes(cp)
    up = 8 * (4 - size)
    down = 8 * (4 - size2)
    if _np_ok():
        vals = (_samples_np(cp, size) << up) >> down
        return _pack_np(vals, size2)
    return _pack_py([(s << up) >> down for s in _samples_py(cp, size)], size2)


def _gcd(a, b):
    while b > 0:
        a, b = b, a % b
    return a


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

    d = _gcd(inrate, outrate)
    inrate //= d
    outrate //= d
    d = _gcd(weightA, weightB)
    weightA //= d
    weightB //= d

    nframes = len(cp) // bytes_per_frame

    if state is None:
        d = -outrate
        prev_i = [0] * nchannels
        cur_i = [0] * nchannels
    else:
        if not isinstance(state, tuple):
            raise TypeError("state must be a tuple or None")
        try:
            d, samps = state
            if len(samps) != nchannels:
                raise error("illegal state argument")
            prev_i = [int(p) for p, c in samps]
            cur_i = [int(c) for p, c in samps]
        except (TypeError, ValueError):
            raise TypeError("ratecv(): illegal state argument")

    if nframes == 0:
        return b"", (d, tuple(zip(prev_i, cur_i)))

    up = 8 * (4 - size)
    down = up

    # Input samples scaled to 32 bits (GETSAMPLE32), per channel, with the
    # state's current sample prepended so that e[n] is "cur" after n frames.
    if _np_ok():
        samples = _samples_np(cp, size) << up
        chans = [_np.concatenate(([cur_i[c]], samples[c::nchannels])) for c in range(nchannels)]
    else:
        samples = [s << up for s in _samples_py(cp, size)]
        chans = [[cur_i[c]] + samples[c::nchannels] for c in range(nchannels)]

    if weightB != 0:
        # The recursive filter needs a sequential pass.
        wa = float(weightA)
        wb = float(weightB)
        for c in range(nchannels):
            e = list(chans[c])
            for n in range(1, len(e)):
                e[n] = int((wa * e[n] + wb * e[n - 1]) / (wa + wb))
            chans[c] = _np.array(e, dtype=_np.int64) if _np_ok() else e

    # Output k is produced once n_k input frames have been consumed, where
    # n_k = ceil((k*inrate - d0)/outrate); at that point d = d0 + n_k*outrate
    # - k*inrate (in [0, outrate)), prev = e[n_k-1] and cur = e[n_k].
    d0 = d
    nout = (nframes * outrate + d0) // inrate + 1
    if nout < 0:
        nout = 0

    if _np_ok():
        k = _np.arange(nout, dtype=_np.int64)
        n_k = -((-(k * inrate - d0)) // outrate)  # ceil division
        d_k = (d0 + n_k * outrate - k * inrate).astype(_np.float64)
        out = _np.empty(nout * nchannels, dtype=_np.int64)
        fout = float(outrate)
        for c in range(nchannels):
            e = chans[c]
            prev = e[n_k - 1].astype(_np.float64)
            cur = e[n_k].astype(_np.float64)
            vals = (prev * d_k + cur * (fout - d_k)) / fout
            # (int) cast in C truncates toward zero, as does astype
            out[c::nchannels] = vals.astype(_np.int64) >> down
        result = _pack_np(out, size)
    else:
        out = []
        fout = float(outrate)
        for k in range(nout):
            n_k = -((-(k * inrate - d0)) // outrate)
            dk = float(d0 + n_k * outrate - k * inrate)
            for c in range(nchannels):
                e = chans[c]
                v = (float(e[n_k - 1]) * dk + float(e[n_k]) * (fout - dk)) / fout
                out.append(int(v) >> down)
        result = _pack_py(out, size)

    d_final = d0 + nframes * outrate - nout * inrate
    new_state = []
    for c in range(nchannels):
        e = chans[c]
        new_state.append((int(e[nframes - 1]), int(e[nframes])))
    return result, (d_final, tuple(new_state))


# ---------------------------------------------------------------- codecs

def _not_implemented(name):
    raise NotImplementedError(
        "%s is not available in pydub's pure-Python audioop fallback; "
        "install the 'audioop-lts' package for the full C implementation" % name)


def lin2ulaw(cp, size):
    _not_implemented("lin2ulaw")


def ulaw2lin(cp, size):
    _not_implemented("ulaw2lin")


def lin2alaw(cp, size):
    _not_implemented("lin2alaw")


def alaw2lin(cp, size):
    _not_implemented("alaw2lin")


def lin2adpcm(cp, size, state):
    _not_implemented("lin2adpcm")


def adpcm2lin(cp, size, state):
    _not_implemented("adpcm2lin")
