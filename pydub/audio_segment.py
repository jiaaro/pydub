import subprocess
from tempfile import TemporaryFile
from StringIO import StringIO
import wave
import audioop

from .utils import _fd_or_path_or_tempfile, db_to_float
from .exceptions import UnsupportedOuputFormat



class AudioSegment(object):
    """
    Note: AudioSegment objects are immutable
    
    slicable using milliseconds. for example: Get the first second of an mp3...
    
    a = AudioSegment.from_mp3(mp3file)
    first_second = a[:1000]
    """
    
    def __init__(self, data=None, *args, **kwargs):
        if kwargs.get('metadata', False):
            # internal use only
            self._data = data
            for attr, val in kwargs.pop('metadata').items():
                setattr(self, attr, val)
        else:
            # normal construction
            data = data if isinstance(data, basestring) else data.read()
            
            raw = wave.open(StringIO(data), 'rb')
            
            raw.rewind()
            self.sample_width = raw.getsampwidth() 
            self.frame_rate = raw.getframerate()
            self.frame_width = len(raw.readframes(1))
            self.channels = raw.getnchannels()
            
            raw.rewind()
            self._data = raw.readframes(float('inf'))
        
        super(AudioSegment, self).__init__(*args, **kwargs)
            
    
    def __len__(self):
        """
        returns the length of this audio segment in milliseconds
        """
        return 1000.0 * self.frame_count() / self.frame_rate
    
    
    def __getitem__(self, millisecond):
        if isinstance(millisecond, slice):
            start = self._parse_position(millisecond.start or 0)
            end = self._parse_position(millisecond.stop or self.frame_count())
            data = self._data[start:end]
        else:
            start = self._parse_position(millisecond)
            end = start + self.frame_count(ms=1)
            data = self._data[start:end]
            
        return self._spawn(data)


    def __add__(self, arg):
        if isinstance(arg, AudioSegment):
            return self.append(arg, crossfade_ms=0)
        else:
            return self.apply_gain(arg)
        
        
    def __sub__(self, arg):
        if isinstance(arg, AudioSegment):
            raise TypeError("AudioSegment objects can't be subtracted from each other")
        else:
            return self.apply_gain(-arg)
        
    
    def __mul__(self, arg):
        """
        If the argument is an AudioSegment, overlay the multiplied audio 
        segment.
        
        
        If it's a number, just use the string multiply operation to repeat the 
        audio so the following would return an AudioSegment that contains the 
        audio of audio_seg eight times
        
        audio_seg * 8
        """
        if isinstance(arg, AudioSegment):
            return self.overlay(arg, position=0, loop=True)
        else:
            return self._spawn(data=self._data*arg)
    
    
    def _spawn(self, data, overrides={}):
        """
        Creates a new audio segment using the meta data from the current one
        and the data passed in. Should be used whenever an AudioSegment is 
        being returned by an operation that alters the current one, since
        AudioSegment objects are immutable.
        """
        # accept lists of data chunks 
        if isinstance(data, list):
            data = ''.join(data)
            
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
        return AudioSegment(data=data, metadata=metadata)
    
    
    @classmethod
    def _sync(cls, seg1, seg2):
        frame_rate = max(seg1.frame_rate, seg2.frame_rate)
        seg1 = seg1.set_frame_rate(frame_rate)
        seg2 = seg2.set_frame_rate(frame_rate)
        
        channels = max(seg1.channels, seg2.channels)
        seg1 = seg1.set_channels(channels)
        seg2 = seg2.set_channels(channels)
        
        return seg1, seg2
    
    
    def _parse_position(self, val):
        if val == float("inf"): return self.frame_count()
        val = self.frame_count(val)
        if val < 0:
            val = self.frame_count() - abs(val)
        return val
    
    
    @classmethod
    def from_mp3(cls, file):
        file = _fd_or_path_or_tempfile(file, 'r', tempfile=False)
        file.seek(0)
        
        output = TemporaryFile()
        
        # read stdin / write stdout
        subprocess.call(['lame', '--mp3input', '--resample', '44.1', '--decode', '-', '-'], stdin=file, stdout=output)
        output.seek(0)    
        
        return cls(data=output)
    
    
    def export(self, out_f=None, format='mp3'):
        if format != 'mp3':
            raise UnsupportedOuputFormat("Only mp3 is supported at present")
        
        if out_f is not None:
            out_f = open(out_f, 'wb') if isinstance(out_f, basestring) else out_f
        else:
            out_f = TemporaryFile()
        
        subprocess.call(['lame', '-rh', '-', '-'], stdin=self._data, stdout=out_f)
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
            return ms * self.frame_rate / 1000
        else:
            return len(self._data) / self.frame_width
    
    
    def set_frame_rate(self, frame_rate):
        if frame_rate == self.frame_rate:
            return self
        
        converted, _ = audioop.ratecv(self._data, self.frame_width/self.channels, self.channels, self.frame_rate, frame_rate, None)
        return self._spawn(data=converted, overrides={'frame_rate': frame_rate})
    
    
    def set_channels(self, channels):
        if channels == self.channels:
            return self
        
        if channels == 2 and self.channels == 1:
            fn = 'tostereo'
        elif channels == 1 and self.channels == 2:
            fn = 'tomono'
            
        fn = getattr(audioop, fn)
        converted = fn(self._data, self.frame_width, 1, 1)

        return self._spawn(data=converted, overrides={'channels': channels})
    
    
    @property
    def rms(self):
        return audioop.rms(self._data, self.frame_width)
    
    
    def apply_gain(self, volume_change):
        return self._spawn(data=audioop.mul(self._data, self.frame_width, db_to_float(float(volume_change))))
    
    
    def overlay(self, seg, position=0, loop=False):
        output = TemporaryFile()
        
        seg1, seg2 = AudioSegment._sync(self, seg)
        frame_width = seg1.frame_width
        spawn = seg1._spawn
        
        start = seg1._parse_position(position)
        output.write(seg1[:start]._data)
        
        # drop down to the raw data
        seg1 = seg1[start:]._data
        seg2 = seg2._data
        index = 0
        seg2_len = len(seg2)
        seg1_len = len(seg1)
        while True:
            remaining = max(0, seg1_len - (index * seg2_len))            
            if seg2_len >= remaining:
                seg2 = seg2[:remaining]
                loop = False
            
            pos = index * seg2_len
            output.write(audioop.add(seg1[pos:pos+seg2_len], seg2, frame_width))
            index += 1
            
            if not loop: break
            
        output.write(seg1[index*seg2_len:])
        
        return spawn(data=output)


    def append(self, seg, crossfade_ms=100):
        output = TemporaryFile()
        
        seg1, seg2 = AudioSegment._sync(self, seg)
        
        if not crossfade_ms:
            return seg1._spawn(data=seg1._data + seg2._data)
        
        seg1 = seg1.fade_out(duration=crossfade_ms)
        seg2 = seg2.fade_in(duration=crossfade_ms)
        crossfade = seg1[-crossfade_ms:] * seg2[:crossfade_ms]
        
        output.write(seg1[:-crossfade_ms]._data)
        output.write(crossfade._data)
        output.write(seg2[crossfade_ms:]._data)
        
        output.seek(0)
        return self._spawn(data=output)
        
        
    def fade(self, to_gain=0, from_gain=0, start=None, end=None, duration=None):
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
        if None not in [duration, end, start]: raise TypeError("Only two of the three arguments, \"start\", \"end\", and \"duration\" may be specified")
        
        # no fade == the same audio
        if to_gain == 0 and from_gain == 0: return self
        
        frames = self.frame_count()
        
        if duration:
            duration = self.frame_count(duration)
        
        start = self._parse_position(start)
        end = self._parse_position(end)
            
        output = []
        
        # original data - up until the crossfade portion, as is
        before_fade = self._data[: (start) * self.frame_width ]
        if from_gain != 0:
            before_fade = audioop.mul(before_fade, self.sample_width, db_to_float(from_gain))
        output.append(before_fade)
        
        scale_step = db_to_float(to_gain)/frames
        
        for i in range(0, duration):
            volume_change = db_to_float(from_gain) + (scale_step * i)
            sample = self.get_sample(start + i)
            sample = audioop.mul(sample, self.sample_width, volume_change)
            
            output.append(sample)
            
        # original data after the crossfade portion, at the new volume
        after_fade = self._data[: (end) * self.frame_width ]
        if to_gain != 0:
            after_fade = audioop.mul(after_fade, self.sample_width, db_to_float(to_gain))
        output.append(after_fade)
        
        return self._spawn(data=output)


    def fade_out(self, duration):
        return self.fade(to_gain=-120, duration=duration, end=float('inf'))
    
    
    def fade_in(self, duration):
        return self.fade(from_gain=-120, duration=duration, start=0)
    
    