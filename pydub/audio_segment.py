from __future__ import division

import array
import os
import subprocess
from tempfile import TemporaryFile, NamedTemporaryFile
import wave
import sys
import struct
from .logging_utils import log_conversion
import base64

try:
    from StringIO import StringIO
except:
    from io import StringIO

from io import BytesIO

try:
    from itertools import izip
except:
    izip = zip

from .utils import (
    _fd_or_path_or_tempfile,
    db_to_float,
    ratio_to_db,
    get_encoder_name,
    get_array_type,
    audioop,
)
from .exceptions import (
    TooManyMissingFrames,
    InvalidDuration,
    InvalidID3TagVersion,
    InvalidTag,
    CouldntDecodeError,
    CouldntEncodeError,
    MissingAudioParameter,
)

if sys.version_info >= (3, 0):
    basestring = str
    xrange = range
    StringIO = BytesIO


class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self

def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


AUDIO_FILE_EXT_ALIASES = {
    "m4a": "mp4",
    "wave": "wav",
}


class AudioSegment(object):
    """
    AudioSegments are *immutable* objects representing segments of audio
    that can be manipulated using python code.

    AudioSegments are slicable using milliseconds.
    for example:
        a = AudioSegment.from_mp3(mp3file)
        first_second = a[:1000] # get the first second of an mp3
        slice = a[5000:10000] # get a slice from 5 to 10 seconds of an mp3
    """
    converter = get_encoder_name()  # either ffmpeg or avconv

    # TODO: remove in 1.0 release
    # maintain backwards compatibility for ffmpeg attr (now called converter)
    @classproperty
    def ffmpeg(cls):
        return cls.converter

    @ffmpeg.setter
    def ffmpeg(cls, val):
        cls.converter = val

    DEFAULT_CODECS = {
        "ogg": "libvorbis"
    }

    def __init__(self, data=None, *args, **kwargs):
        self.sample_width = kwargs.pop("sample_width", None)
        self.frame_rate = kwargs.pop("frame_rate", None)
        self.channels = kwargs.pop("channels", None)

        audio_params = (self.sample_width, self.frame_rate, self.channels)

        # prevent partial specification of arguments
        if any(audio_params) and None in audio_params:
            raise MissingAudioParameter("Either all audio parameters or no parameter must be specified")

        # all arguments are given
        elif self.sample_width is not None:
            if len(data) % (self.sample_width * self.channels) != 0:
                raise ValueError("data length must be a multiple of '(sample_width * channels)'")

            self.frame_width = self.channels * self.sample_width
            self._data = data

        # keep support for 'metadata' until audio params are used everywhere
        elif kwargs.get('metadata', False):
            # internal use only
            self._data = data
            for attr, val in kwargs.pop('metadata').items():
                setattr(self, attr, val)
        else:
            # normal construction
            try:
                data = data if isinstance(data, (basestring, bytes)) else data.read()
            except(OSError):
                d = b''
                reader = data.read(2**31-1)
                while reader:
                    d += reader
                    reader = data.read(2**31-1)
                data = d

            raw = wave.open(StringIO(data), 'rb')

            raw.rewind()
            self.channels = raw.getnchannels()
            self.sample_width = raw.getsampwidth()
            self.frame_rate = raw.getframerate()
            self.frame_width = self.channels * self.sample_width

            raw.rewind()

            # the "or b''" base case is a work-around for a python 3.4
            # see https://github.com/jiaaro/pydub/pull/107
            self._data = raw.readframes(float('inf')) or b''

        # Convert 24-bit audio to 32-bit audio.
        # (stdlib audioop and array modules do not support 24-bit data)
        if self.sample_width == 3:
            byte_buffer = BytesIO()

            # Workaround for python 2 vs python 3. _data in 2.x are length-1 strings,
            # And in 3.x are ints.
            pack_fmt = 'BBB' if isinstance(self._data[0], int) else 'ccc'

            # This conversion maintains the 24 bit values.  The values are
            # not scaled up to the 32 bit range.  Other conversions could be
            # implemented.
            i = iter(self._data)
            padding = {False: b'\x00', True: b'\xFF'}
            for b0, b1, b2 in izip(i, i, i):
                byte_buffer.write(padding[b2 > b'\x7f'[0]])
                old_bytes = struct.pack(pack_fmt, b0, b1, b2)
                byte_buffer.write(old_bytes)


            self._data = byte_buffer.getvalue()
            self.sample_width = 4
            self.frame_width = self.channels * self.sample_width

        super(AudioSegment, self).__init__(*args, **kwargs)

    @property
    def raw_data(self):
        """
        public access to the raw audio data as a bytestring
        """
        return self._data


    def get_array_of_samples(self):
        """
        returns the raw_data as an array of samples
        """
        return array.array(self.array_type, self._data)

    @property
    def array_type(self):
        return get_array_type(self.sample_width * 8)

    def __len__(self):
        """
        returns the length of this audio segment in milliseconds
        """
        return round(1000 * (self.frame_count() / self.frame_rate))

    def __eq__(self, other):
        try:
            return self._data == other._data
        except:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return (self[i] for i in xrange(len(self)))

    def __getitem__(self, millisecond):
        if isinstance(millisecond, slice):
            start = millisecond.start if millisecond.start is not None else 0
            end = millisecond.stop if millisecond.stop is not None \
                else len(self)

            start = min(start, len(self))
            end = min(end, len(self))
        else:
            start = millisecond
            end = millisecond + 1

        start = self._parse_position(start) * self.frame_width
        end = self._parse_position(end) * self.frame_width
        data = self._data[start:end]

        # ensure the output is as long as the requester is expecting
        expected_length = end - start
        missing_frames = (expected_length - len(data)) // self.frame_width
        if missing_frames:
            if missing_frames > self.frame_count(ms=2):
                raise TooManyMissingFrames(
                    "You should never be filling in "
                    "   more than 2 ms with silence here, "
                    "missing frames: %s" % missing_frames)
            silence = audioop.mul(data[:self.frame_width],
                                  self.sample_width, 0)
            data += (silence * missing_frames)

        return self._spawn(data)

    def get_sample_slice(self, start_sample=None, end_sample=None):
        """
        Get a section of the audio segment by sample index.

        NOTE: Negative indices do *not* address samples backword
        from the end of the audio segment like a python list.
        This is intentional.
        """
        max_val = int(self.frame_count())

        def bounded(val, default):
            if val is None:
                return default
            if val < 0:
                return 0
            if val > max_val:
                return max_val
            return val

        start_i = bounded(start_sample, 0) * self.frame_width
        end_i = bounded(end_sample, max_val) * self.frame_width

        data = self._data[start_i:end_i]
        return self._spawn(data)

    def __add__(self, arg):
        if isinstance(arg, AudioSegment):
            return self.append(arg, crossfade=0)
        else:
            return self.apply_gain(arg)

    def __radd__(self, rarg):
        """
        Permit use of sum() builtin with an iterable of AudioSegments
        """
        if rarg == 0:
            return self
        raise TypeError("Gains must be the second addend after the "
                        "AudioSegment")

    def __sub__(self, arg):
        if isinstance(arg, AudioSegment):
            raise TypeError("AudioSegment objects can't be subtracted from "
                            "each other")
        else:
            return self.apply_gain(-arg)

    def __mul__(self, arg):
        """
        If the argument is an AudioSegment, overlay the multiplied audio
        segment.

        If it's a number, just use the string multiply operation to repeat the
        audio.

        The following would return an AudioSegment that contains the
        audio of audio_seg eight times

        `audio_seg * 8`
        """
        if isinstance(arg, AudioSegment):
            return self.overlay(arg, position=0, loop=True)
        else:
            return self._spawn(data=self._data * arg)

    def _spawn(self, data, overrides={}):
        """
        Creates a new audio segment using the metadata from the current one
        and the data passed in. Should be used whenever an AudioSegment is
        being returned by an operation that would alters the current one,
        since AudioSegment objects are immutable.
        """
        # accept lists of data chunks
        if isinstance(data, list):
            data = b''.join(data)

        if isinstance(data, array.array):
            try:
                data = data.tobytes()
            except:
                data = data.tostring()

        # accept file-like objects
        if hasattr(data, 'read'):
            if hasattr(data, 'seek'):
                data.seek(0)
            data = data.read()

        metadata = {
            'sample_width': self.sample_width,
            'frame_rate': self.frame_rate,
            'frame_width': self.frame_width,
            'channels': self.channels
        }
        metadata.update(overrides)
        return self.__class__(data=data, metadata=metadata)

    @classmethod
    def _sync(cls, seg1, seg2):
        s1_len, s2_len = len(seg1), len(seg2)

        channels = max(seg1.channels, seg2.channels)
        seg1 = seg1.set_channels(channels)
        seg2 = seg2.set_channels(channels)

        frame_rate = max(seg1.frame_rate, seg2.frame_rate)
        seg1 = seg1.set_frame_rate(frame_rate)
        seg2 = seg2.set_frame_rate(frame_rate)

        sample_width = max(seg1.sample_width, seg2.sample_width)
        seg1 = seg1.set_sample_width(sample_width)
        seg2 = seg2.set_sample_width(sample_width)

        return seg1, seg2

    def _parse_position(self, val):
        if val < 0:
            val = len(self) - abs(val)
        val = self.frame_count(ms=len(self)) if val == float("inf") else \
            self.frame_count(ms=val)
        return int(val)

    @classmethod
    def empty(cls):
        return cls(b'', metadata={
            "channels": 1,
            "sample_width": 1,
            "frame_rate": 1,
            "frame_width": 1
        })

    @classmethod
    def silent(cls, duration=1000, frame_rate=11025):
        """
        Generate a silent audio segment.
        duration specified in milliseconds (default duration: 1000ms, default frame_rate: 11025).
        """
        frames = int(frame_rate * (duration / 1000.0))
        data = b"\0\0" * frames
        return cls(data, metadata={"channels": 1,
                                   "sample_width": 2,
                                   "frame_rate": frame_rate,
                                   "frame_width": 2})

    @classmethod
    def from_file(cls, file, format=None, **kwargs):
        orig_file = file
        file = _fd_or_path_or_tempfile(file, 'rb', tempfile=False)

        if format:
            format = format.lower()
            format = AUDIO_FILE_EXT_ALIASES.get(format, format)

        def is_format(f):
            f = f.lower()
            if format == f:
                return True
            if isinstance(orig_file, basestring):
                return orig_file.lower().endswith(".{0}".format(f))
            return False

        if is_format("wav"):
            try:
                return cls._from_safe_wav(file)
            except:
                file.seek(0)
        elif is_format("raw") or is_format("pcm"):
            sample_width = kwargs['sample_width']
            frame_rate = kwargs['frame_rate']
            channels = kwargs['channels']
            metadata = {
                'sample_width': sample_width,
                'frame_rate': frame_rate,
                'channels': channels,
                'frame_width': channels * sample_width
            }
            return cls(data=file.read(), metadata=metadata)

        input_file = NamedTemporaryFile(mode='wb', delete=False)
        try:
            input_file.write(file.read())
        except(OSError):
            input_file.flush()
            input_file.close()
            input_file = NamedTemporaryFile(mode='wb', delete=False, buffering=2**31-1)
            file = open(orig_file, buffering=2**13-1, mode='rb')
            reader = file.read(2**31-1)
            while reader:
                input_file.write(reader)
                reader = file.read(2**31-1)
        input_file.flush()

        output = NamedTemporaryFile(mode="rb", delete=False)

        conversion_command = [cls.converter,
                              '-y',  # always overwrite existing files
                              ]

        # If format is not defined
        # ffmpeg/avconv will detect it automatically
        if format:
            conversion_command += ["-f", format]

        conversion_command += [
            "-i", input_file.name,  # input_file options (filename last)
            "-vn",  # Drop any video streams if there are any
            "-f", "wav",  # output options (filename last)
            output.name
        ]

        log_conversion(conversion_command)

        p = subprocess.Popen(conversion_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_out, p_err = p.communicate()

        if p.returncode != 0:
            raise CouldntDecodeError("Decoding failed. ffmpeg returned error code: {0}\n\nOutput from ffmpeg/avlib:\n\n{1}".format(p.returncode, p_err))

        obj = cls._from_safe_wav(output)

        input_file.close()
        output.close()
        os.unlink(input_file.name)
        os.unlink(output.name)

        return obj

    @classmethod
    def from_mp3(cls, file):
        return cls.from_file(file, 'mp3')

    @classmethod
    def from_flv(cls, file):
        return cls.from_file(file, 'flv')

    @classmethod
    def from_ogg(cls, file):
        return cls.from_file(file, 'ogg')

    @classmethod
    def from_wav(cls, file):
        return cls.from_file(file, 'wav')

    @classmethod
    def from_raw(cls, file, **kwargs):
        return cls.from_file(file, 'raw', sample_width=kwargs['sample_width'], frame_rate=kwargs['frame_rate'], channels=kwargs['channels'])

    @classmethod
    def _from_safe_wav(cls, file):
        file = _fd_or_path_or_tempfile(file, 'rb', tempfile=False)
        file.seek(0)
        return cls(data=file)

    def export(self, out_f=None, format='mp3', codec=None, bitrate=None, parameters=None, tags=None, id3v2_version='4'):
        """
        Export an AudioSegment to a file with given options

        out_f (string):
            Path to destination audio file

        format (string)
            Format for destination audio file.
            ('mp3', 'wav', 'raw', 'ogg' or other ffmpeg/avconv supported files)

        codec (string)
            Codec used to encoding for the destination.

        bitrate (string)
            Bitrate used when encoding destination file. (64, 92, 128, 256, 312k...)
            Each codec accepts different bitrate arguments so take a look at the
            ffmpeg documentation for details (bitrate usually shown as -b, -ba or
            -a:b).

        parameters (string)
            Aditional ffmpeg/avconv parameters

        tags (dict)
            Set metadata information to destination files
            usually used as tags. ({title='Song Title', artist='Song Artist'})

        id3v2_version (string)
            Set ID3v2 version for tags. (default: '4')
        """
        id3v2_allowed_versions = ['3', '4']

        out_f = _fd_or_path_or_tempfile(out_f, 'wb+')
        out_f.seek(0)

        if format == "raw":
            out_f.write(self._data)
            out_f.seek(0)
            return out_f

        # for wav output we can just write the data directly to out_f
        if format == "wav":
            data = out_f
        else:
            data = NamedTemporaryFile(mode="wb", delete=False)

        wave_data = wave.open(data, 'wb')
        wave_data.setnchannels(self.channels)
        wave_data.setsampwidth(self.sample_width)
        wave_data.setframerate(self.frame_rate)
        # For some reason packing the wave header struct with
        # a float in python 2 doesn't throw an exception
        wave_data.setnframes(int(self.frame_count()))
        wave_data.writeframesraw(self._data)
        wave_data.close()

        # for wav files, we're done (wav data is written directly to out_f)
        if format == 'wav':
            return out_f

        output = NamedTemporaryFile(mode="w+b", delete=False)

        # build converter command to export
        conversion_command = [
            self.converter,
            '-y',  # always overwrite existing files
            "-f", "wav", "-i", data.name,  # input options (filename last)
        ]

        if codec is None:
            codec = self.DEFAULT_CODECS.get(format, None)

        if codec is not None:
            # force audio encoder
            conversion_command.extend(["-acodec", codec])

        if bitrate is not None:
            conversion_command.extend(["-b:a", bitrate])

        if parameters is not None:
            # extend arguments with arbitrary set
            conversion_command.extend(parameters)

        if tags is not None:
            if not isinstance(tags, dict):
                raise InvalidTag("Tags must be a dictionary.")
            else:
                # Extend converter command with tags
                # print(tags)
                for key, value in tags.items():
                    conversion_command.extend(
                        ['-metadata', '{0}={1}'.format(key, value)])

                if format == 'mp3':
                    # set id3v2 tag version
                    if id3v2_version not in id3v2_allowed_versions:
                        raise InvalidID3TagVersion(
                            "id3v2_version not allowed, allowed versions: %s" % id3v2_allowed_versions)
                    conversion_command.extend([
                        "-id3v2_version",  id3v2_version
                    ])

        if sys.platform == 'darwin':
            conversion_command.extend(["-write_xing", "0"])

        conversion_command.extend([
            "-f", format, output.name,  # output options (filename last)
        ])

        log_conversion(conversion_command)

        # read stdin / write stdout
        p = subprocess.Popen(conversion_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_out, p_err = p.communicate()

        if p.returncode != 0:
            raise CouldntEncodeError("Encoding failed. ffmpeg/avlib returned error code: {0}\n\nOutput from ffmpeg/avlib:\n\n{1}".format(p.returncode, p_err))

        output.seek(0)
        out_f.write(output.read())

        data.close()
        output.close()

        os.unlink(data.name)
        os.unlink(output.name)

        out_f.seek(0)
        return out_f

    def get_frame(self, index):
        frame_start = index * self.frame_width
        frame_end = frame_start + self.frame_width
        return self._data[frame_start:frame_end]

    def frame_count(self, ms=None):
        """
        returns the number of frames for the given number of milliseconds, or
            if not specified, the number of frames in the whole AudioSegment
        """
        if ms is not None:
            return ms * (self.frame_rate / 1000.0)
        else:
            return float(len(self._data) // self.frame_width)

    def set_sample_width(self, sample_width):
        if sample_width == self.sample_width:
            return self

        data = self._data

        if self.sample_width == 1:
            data = audioop.bias(data, 1, -128)

        if data:
            data = audioop.lin2lin(data, self.sample_width, sample_width)

        if sample_width == 1:
            data = audioop.bias(data, 1, 128)

        frame_width = self.channels * sample_width
        return self._spawn(data, overrides={'sample_width': sample_width,
                                            'frame_width': frame_width})

    def set_frame_rate(self, frame_rate):
        if frame_rate == self.frame_rate:
            return self

        if self._data:
            converted, _ = audioop.ratecv(self._data, self.sample_width,
                                          self.channels, self.frame_rate,
                                          frame_rate, None)
        else:
            converted = self._data

        return self._spawn(data=converted,
                           overrides={'frame_rate': frame_rate})

    def set_channels(self, channels):
        if channels == self.channels:
            return self

        if channels == 2 and self.channels == 1:
            fn = audioop.tostereo
            frame_width = self.frame_width * 2
        elif channels == 1 and self.channels == 2:
            fn = audioop.tomono
            frame_width = self.frame_width // 2

        converted = fn(self._data, self.sample_width, 1, 1)

        return self._spawn(data=converted,
                           overrides={
                               'channels': channels,
                               'frame_width': frame_width})

    def split_to_mono(self):
        if self.channels == 1:
            return [self]

        left_channel = audioop.tomono(self._data, self.sample_width, 1, 0)
        right_channel = audioop.tomono(self._data, self.sample_width, 0, 1)

        return [self._spawn(data=left_channel,
                            overrides={'channels': 1,
                                       'frame_width': self.sample_width}),
                self._spawn(data=right_channel,
                            overrides={'channels': 1,
                                       'frame_width': self.sample_width})]

    @property
    def rms(self):
        if self.sample_width == 1:
            return self.set_sample_width(2).rms
        else:
            return audioop.rms(self._data, self.sample_width)

    @property
    def dBFS(self):
        rms = self.rms
        if not rms:
            return -float("infinity")
        return ratio_to_db(self.rms / self.max_possible_amplitude)

    @property
    def max(self):
        return audioop.max(self._data, self.sample_width)

    @property
    def max_possible_amplitude(self):
        bits = self.sample_width * 8
        max_possible_val = (2 ** bits)

        # since half is above 0 and half is below the max amplitude is divided
        return max_possible_val / 2

    @property
    def max_dBFS(self):
        return ratio_to_db(self.max, self.max_possible_amplitude)

    @property
    def duration_seconds(self):
        return self.frame_rate and self.frame_count() / self.frame_rate or 0.0

    def apply_gain(self, volume_change):
        return self._spawn(data=audioop.mul(self._data, self.sample_width,
                                            db_to_float(float(volume_change))))

    def overlay(self, seg, position=0, loop=False, times=None):
        """
        Overlay the provided segment on to this segment starting at the
        specificed position and using the specfied looping beahvior.

        seg (AudioSegment):
            The audio segment to overlay on to this one.

        position (optional int):
            The position to start overlaying the provided segment in to this
            one.

        loop (optional bool):
            Loop seg as many times as necessary to match this segment's length.
            Overrides loops param.

        times (optional int):
            Loop seg the specified number of times or until it matches this
            segment's length. 1 means once, 2 means twice, ... 0 would make the
            call a no-op
        """

        if loop:
            # match loop=True's behavior with new times (count) mechinism.
            times = -1
        elif times is None:
            # no times specified, just once through
            times = 1
        elif times == 0:
            # it's a no-op, make a copy since we never mutate
            return self._spawn(self._data)

        output = StringIO()

        seg1, seg2 = AudioSegment._sync(self, seg)
        sample_width = seg1.sample_width
        spawn = seg1._spawn

        output.write(seg1[:position]._data)

        # drop down to the raw data
        seg1 = seg1[position:]._data
        seg2 = seg2._data
        pos = 0
        seg1_len = len(seg1)
        seg2_len = len(seg2)
        while times:
            remaining = max(0, seg1_len - pos)
            if seg2_len >= remaining:
                seg2 = seg2[:remaining]
                seg2_len = remaining
                # we've hit the end, we're done looping (if we were) and this
                # is our last go-around
                times = 1

            output.write(audioop.add(seg1[pos:pos + seg2_len], seg2,
                                     sample_width))
            pos += seg2_len

            # dec times to break our while loop (eventually)
            times -= 1

        output.write(seg1[pos:])

        return spawn(data=output)

    def append(self, seg, crossfade=100):
        seg1, seg2 = AudioSegment._sync(self, seg)

        if not crossfade:
            return seg1._spawn(seg1._data + seg2._data)

        xf = seg1[-crossfade:].fade(to_gain=-120, start=0, end=float('inf'))
        xf *= seg2[:crossfade].fade(from_gain=-120, start=0, end=float('inf'))

        output = TemporaryFile()

        output.write(seg1[:-crossfade]._data)
        output.write(xf._data)
        output.write(seg2[crossfade:]._data)

        output.seek(0)
        return seg1._spawn(data=output)

    def fade(self, to_gain=0, from_gain=0, start=None, end=None,
             duration=None):
        """
        Fade the volume of this audio segment.

        to_gain (float):
            resulting volume_change in db

        start (int):
            default = beginning of the segment
            when in this segment to start fading in milliseconds

        end (int):
            default = end of the segment
            when in this segment to start fading in milliseconds

        duration (int):
            default = until the end of the audio segment
            the duration of the fade
        """
        if None not in [duration, end, start]:
            raise TypeError('Only two of the three arguments, "start", '
                            '"end", and "duration" may be specified')

        # no fade == the same audio
        if to_gain == 0 and from_gain == 0:
            return self

        start = min(len(self), start) if start is not None else None
        end = min(len(self), end) if end is not None else None

        if start is not None and start < 0:
            start += len(self)
        if end is not None and end < 0:
            end += len(self)

        if duration is not None and duration < 0:
            raise InvalidDuration("duration must be a positive integer")

        if duration:
            if start is not None:
                end = start + duration
            elif end is not None:
                start = end - duration
        else:
            duration = end - start

        from_power = db_to_float(from_gain)

        output = []

        # original data - up until the crossfade portion, as is
        before_fade = self[:start]._data
        if from_gain != 0:
            before_fade = audioop.mul(before_fade,
                                      self.sample_width,
                                      from_power)
        output.append(before_fade)

        gain_delta = db_to_float(to_gain) - from_power

        # fades longer than 100ms can use coarse fading (one gain step per ms),
        # shorter fades will have audible clicks so they use precise fading
        #(one gain step per sample)
        if duration > 100:
            scale_step = gain_delta / duration

            for i in range(duration):
                volume_change = from_power + (scale_step * i)
                chunk = self[start + i]
                chunk = audioop.mul(chunk._data,
                                    self.sample_width,
                                    volume_change)

                output.append(chunk)
        else:
            start_frame = self.frame_count(ms=start)
            end_frame = self.frame_count(ms=end)
            fade_frames = end_frame - start_frame
            scale_step = gain_delta / fade_frames

            for i in range(int(fade_frames)):
                volume_change = from_power + (scale_step * i)
                sample = self.get_frame(int(start_frame + i))
                sample = audioop.mul(sample, self.sample_width, volume_change)

                output.append(sample)

        # original data after the crossfade portion, at the new volume
        after_fade = self[end:]._data
        if to_gain != 0:
            after_fade = audioop.mul(after_fade,
                                     self.sample_width,
                                     db_to_float(to_gain))
        output.append(after_fade)

        return self._spawn(data=output)

    def fade_out(self, duration):
        return self.fade(to_gain=-120, duration=duration, end=float('inf'))

    def fade_in(self, duration):
        return self.fade(from_gain=-120, duration=duration, start=0)

    def reverse(self):
        return self._spawn(
            data=audioop.reverse(self._data, self.sample_width)
        )

    def _repr_html_(self):
            src = """
                    <audio controls>
                        <source src="data:audio/mpeg;base64,{base64}" type="audio/mpeg"/>
                        Your browser does not support the audio element.
                    </audio>
                  """
            fh = self.export()
            data = base64.b64encode(fh.read()).decode('ascii')
            return src.format(base64=data)

from . import effects