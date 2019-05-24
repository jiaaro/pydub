from __future__ import division

import json
import os
import re
import sys
from subprocess import Popen, PIPE
from math import log, ceil
from tempfile import TemporaryFile
from warnings import warn
from functools import wraps

try:
    import audioop
except ImportError:
    import pyaudioop as audioop

if sys.version_info >= (3, 0):
    basestring = str

FRAME_WIDTHS = {
    8: 1,
    16: 2,
    32: 4,
}
ARRAY_TYPES = {
    8: "b",
    16: "h",
    32: "i",
}
ARRAY_RANGES = {
    8: (-0x80, 0x7f),
    16: (-0x8000, 0x7fff),
    32: (-0x80000000, 0x7fffffff),
}


def replace_last(old, new, s):
    li = s.rsplit(old, 1)
    return new.join(li)


def get_frame_width(bit_depth):
    return FRAME_WIDTHS[bit_depth]


def get_array_type(bit_depth, signed=True):
    t = ARRAY_TYPES[bit_depth]
    if not signed:
        t = t.upper()
    return t


def get_min_max_value(bit_depth):
    return ARRAY_RANGES[bit_depth]


def _fd_or_path_or_tempfile(fd, mode='w+b', tempfile=True):
    close_fd = False
    if fd is None and tempfile:
        fd = TemporaryFile(mode=mode)
        close_fd = True

    if isinstance(fd, basestring):
        fd = open(fd, mode=mode)
        close_fd = True

    try:
        if isinstance(fd, os.PathLike):
            fd = open(fd, mode=mode)
            close_fd = True
    except AttributeError:
        # module os has no attribute PathLike, so we're on python < 3.6.
        # The protocol we're trying to support doesn't exist, so just pass.
        pass

    return fd, close_fd


def db_to_float(dB, using_amplitude=True):
    """
    Convert the input dB value to a float which represents the equivalent
    ratio in power.

    Parameters
    ----------

    dB
        The value to convert

    using_amplitude : bool, optional
        default - True
    """
    dB = float(dB)
    if using_amplitude:
        return 10 ** (dB / 20)
    else: # using power
        return 10 ** (dB / 10)


def ratio_to_db(ratio, val2=None, using_amplitude=True):
    """
    Convert the input ratio value to a dB value which represents the
    equivalent to the ratio in power represented by the multiplier passed in.

    Parameters
    ----------

    ratio
        The value to convert, or the numerator of this value

    val2 : optional
        The denominator of the value to convert

    using_amplitude : bool, optional
        default - True
    """

    ratio = float(ratio)

    # accept 2 values and use the ratio of val1 to val2
    if val2 is not None:
        ratio = ratio / val2

    # special case for multiply-by-zero (convert to silence)
    if ratio == 0:
        return -float('inf')

    if using_amplitude:
        return 20 * log(ratio, 10)
    else: # using power
        return 10 * log(ratio, 10)


def register_pydub_effect(fn, name=None):
    """
    decorator for adding pydub effects to the AudioSegment objects.
    example use:
        @register_pydub_effect
        def normalize(audio_segment):
            ...
    or you can specify a name:
        @register_pydub_effect("normalize")
        def normalize_audio_segment(audio_segment):
            ...
    """

    if isinstance(fn, basestring):
        name = fn
        return lambda fn: register_pydub_effect(fn, name)

    if name is None:
        name = fn.__name__

    from .audio_segment import AudioSegment
    setattr(AudioSegment, name, fn)
    return fn


def make_chunks(audio_segment, chunk_length):
    """
    Break an AudioSegment into chunks that are <chunk_length> milliseconds
    long (e.g. if chunk_length is 50, then you'll get a list of 50 millisecond
    long audio segments back). The last chunk can be shorter.
    """
    number_of_chunks = ceil(len(audio_segment) / float(chunk_length))
    return [audio_segment[i * chunk_length:(i + 1) * chunk_length]
            for i in range(int(number_of_chunks))]


def which(program):
    """
    Mimics behavior of UNIX which command.
    """
    # Add .exe program extension for windows support
    if os.name == "nt" and not program.endswith(".exe"):
        program += ".exe"

    envdir_list = [os.curdir] + os.environ["PATH"].split(os.pathsep)

    for envdir in envdir_list:
        program_path = os.path.join(envdir, program)
        if os.path.isfile(program_path) and os.access(program_path, os.X_OK):
            return program_path


def get_name(*choices, **kwargs):
    """
    Helper function for get_encoder_name, get player_name, and get_prober_name
    """
    choices = list(choices)
    for choice in choices:
        if which(choice):
            return choice
    else:
        raise ValueError("choices cannot be empty")

    default_choice = kwargs.pop("default", choices[0])

    # should raise exception
    warn("Couldn't find %s - " +
         "defaulting to %s, but may not work" %
         (replace_last(", ", " or ", ", ".join(choices)), default_choice),
         RuntimeWarning)
    return default_choice


def get_encoder_name():
    """
    Return default encoder application for system, either avconv or ffmpeg
    """
    return get_name("avconv", "ffmpeg", default="ffmpeg")


def get_player_name():
    """
    Return default player application for system, either avplay or ffplay
    """
    return get_name("avplay", "ffplay", default="ffplay")


def get_prober_name():
    """
    Return default probe application for system, either avprobe or ffprobe
    """
    return get_name("avprobe", "ffprobe", default="ffprobe")


def fsdecode(filename):
    """Wrapper for os.fsdecode which was introduced in python 3.2."""

    if sys.version_info >= (3, 2):
        PathLikeTypes = (basestring, bytes)
        if sys.version_info >= (3, 6):
            PathLikeTypes += (os.PathLike,)
        if isinstance(filename, PathLikeTypes):
            return os.fsdecode(filename)
    else:
        if isinstance(filename, bytes):
            return filename.decode(sys.getfilesystemencoding())
        if isinstance(filename, basestring):
            return filename

    raise TypeError("type {0} not accepted by fsdecode".format(type(filename)))


def get_extra_info(stderr):
    """
    avprobe sometimes gives more information on stderr than
    on the json output. The information has to be extracted
    from stderr of the format of:
    '    Stream #0:0: Audio: flac, 88200 Hz, stereo, s32 (24 bit)'
    or (macOS version):
    '    Stream #0:0: Audio: vorbis'
    '      44100 Hz, stereo, fltp, 320 kb/s'

    :type stderr: str
    :rtype: list of dict
    """
    extra_info = {}

    re_stream = r'(?P<space_start> +)Stream #0[:\.]' + \
                r'(?P<stream_id>([0-9]+))(?P<content_0>.+)\n?' + \
                r'((?P<space_end> +)(?P<content_1>.+))?'
    for i in re.finditer(re_stream, stderr):
        if i.group('space_end') is not None and \
                len(i.group('space_start')) <= len(i.group('space_end')):
            content_line = ','.join(
                [i.group('content_0'), i.group('content_1')])
        else:
            content_line = i.group('content_0')
        tokens = [x.strip() for x in re.split('[:,]', content_line) if x]
        extra_info[int(i.group('stream_id'))] = tokens
    return extra_info


def mediainfo_json(filepath, read_ahead_limit=-1):
    """
    Return a json dictionary containing media info
    (codec, duration, size, bitrate, etc) from filepath
    """
    prober = get_prober_name()
    command_args = [
        "-v", "info",
        "-show_format",
        "-show_streams",
    ]
    try:
        command_args += [fsdecode(filepath)]
        stdin_parameter = None
        stdin_data = None
    except TypeError:
        if prober == 'ffprobe':
            command_args += ["-read_ahead_limit", str(read_ahead_limit),
                             "cache:pipe:0"]
        else:
            command_args += ["-"]
        stdin_parameter = PIPE
        file, close_file = _fd_or_path_or_tempfile(
            filepath, 'rb', tempfile=False)
        file.seek(0)
        stdin_data = file.read()
        if close_file:
            file.close()

    command = [prober, '-of', 'json'] + command_args
    res = Popen(command, stdin=stdin_parameter, stdout=PIPE, stderr=PIPE)
    output, stderr = res.communicate(input=stdin_data)
    output = output.decode("utf-8", 'ignore')
    stderr = stderr.decode("utf-8", 'ignore')

    info = json.loads(output)

    if not info:
        # If ffprobe didn't give any information, just return it
        # (for example, because the file doesn't exist)
        return info

    extra_info = get_extra_info(stderr)

    audio_streams = [x for x in info['streams'] if x['codec_type'] == 'audio']
    if len(audio_streams) == 0:
        return info

    # We just operate on the first audio stream in case there are more
    stream = audio_streams[0]

    def set_property(stream, prop, value):
        if prop not in stream or stream[prop] == 0:
            stream[prop] = value

    for token in extra_info[stream['index']]:
        m = re.match('([su]([0-9]{1,2})p?) \(([0-9]{1,2}) bit\)$', token)
        m2 = re.match('([su]([0-9]{1,2})p?)( \(default\))?$', token)
        if m:
            set_property(stream, 'sample_fmt', m.group(1))
            set_property(stream, 'bits_per_sample', int(m.group(2)))
            set_property(stream, 'bits_per_raw_sample', int(m.group(3)))
        elif m2:
            set_property(stream, 'sample_fmt', m2.group(1))
            set_property(stream, 'bits_per_sample', int(m2.group(2)))
            set_property(stream, 'bits_per_raw_sample', int(m2.group(2)))
        elif re.match('(flt)p?( \(default\))?$', token):
            set_property(stream, 'sample_fmt', token)
            set_property(stream, 'bits_per_sample', 32)
            set_property(stream, 'bits_per_raw_sample', 32)
        elif re.match('(dbl)p?( \(default\))?$', token):
            set_property(stream, 'sample_fmt', token)
            set_property(stream, 'bits_per_sample', 64)
            set_property(stream, 'bits_per_raw_sample', 64)
    return info


def mediainfo(filepath):
    """
    Return a dictionary containing media info
    (codec, duration, size, bitrate, etc) from filepath
    """

    prober = get_prober_name()
    command_args = [
        "-v", "quiet",
        "-show_format",
        "-show_streams",
        filepath
    ]

    command = [prober, '-of', 'old'] + command_args
    res = Popen(command, stdout=PIPE)
    output = res.communicate()[0].decode("utf-8")

    if res.returncode != 0:
        command = [prober] + command_args
        output = Popen(command, stdout=PIPE).communicate()[0].decode("utf-8")

    rgx = re.compile(r"(?:(?P<inner_dict>.*?):)?(?P<key>.*?)\=(?P<value>.*?)$")
    info = {}

    if sys.platform == 'win32':
        output = output.replace("\r", "")

    for line in output.split("\n"):
        # print(line)
        mobj = rgx.match(line)

        if mobj:
            # print(mobj.groups())
            inner_dict, key, value = mobj.groups()

            if inner_dict:
                try:
                    info[inner_dict]
                except KeyError:
                    info[inner_dict] = {}
                info[inner_dict][key] = value
            else:
                info[key] = value

    return info


def cache_codecs(function):
    cache = {}

    @wraps(function)
    def wrapper():
        try:
            return cache[0]
        except:
            cache[0] = function()
            return cache[0]

    return wrapper


@cache_codecs
def get_supported_codecs():
    encoder = get_encoder_name()
    command = [encoder, "-codecs"]
    res = Popen(command, stdout=PIPE, stderr=PIPE)
    output = res.communicate()[0].decode("utf-8")
    if res.returncode != 0:
        return []

    if sys.platform == 'win32':
        output = output.replace("\r", "")

    rgx = re.compile(r"^([D.][E.][AVS.][I.][L.][S.]) (\w*) +(.*)")
    decoders = set()
    encoders = set()
    for line in output.split('\n'):
        match = rgx.match(line.strip())
        if not match:
            continue
        flags, codec, name = match.groups()

        if flags[0] == 'D':
            decoders.add(codec)

        if flags[1] == 'E':
            encoders.add(codec)

    return (decoders, encoders)


def get_supported_decoders():
    return get_supported_codecs()[0]


def get_supported_encoders():
    return get_supported_codecs()[1]
