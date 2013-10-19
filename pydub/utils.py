from __future__ import division

from tempfile import TemporaryFile
from math import log, ceil, floor
import sys

if sys.version_info >= (3, 0):
    basestring = str

def _fd_or_path_or_tempfile(fd, mode='w+b', tempfile=True):
    if fd is None and tempfile:
        fd = TemporaryFile(mode=mode)

    if isinstance(fd, basestring):
        fd = open(fd, mode=mode)

    return fd

def db_to_float(db):
    """
    Converts the input db to a float, which represents the equivalent
    ratio in power.
    """
    db = float(db)
    return 10 ** (db / 10)

def ratio_to_db(ratio, val2=None):
    """
    Converts the input float to db, which represents the equivalent
    to the ratio in power represented by the multiplier passed in.
    """
    ratio = float(ratio)

    # accept 2 values and use the ratio of val1 to val2
    if val2 is not None:
        ratio = ratio / val2

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
    Breaks an AudioSegment into chunks that are <chunk_length> milliseconds
    long.
    
    if chunk_length is 50 then you'll get a list of 50 millisecond long audio
    segments back (except the last one, which can be shorter)
    """
    number_of_chunks = ceil(len(audio_segment)/float(chunk_length))
    return [audio_segment[i*chunk_length:(i+1)*chunk_length] 
            for i in range(int(number_of_chunks))]
