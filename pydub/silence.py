"""
Various functions for finding/manipulating silence in AudioSegments
"""
import itertools
import numpy as np

from .utils import db_to_float


def _convert_to_numpy(audio_segment):
    """
    Returns a numpy array view of the raw samples of an AudioSegment,
    with shape (number of frames, channels).
    
    Does not allocate any additional memory.
    
    audio_segment - the segment to convert into a numpy array
    """
    dtype = {
        1: np.int8,
        2: np.int16,
        4: np.int32
    }[audio_segment.sample_width]
    x = np.frombuffer(audio_segment.raw_data, dtype=dtype).reshape(-1, audio_segment.channels)
    return x


def detect_silence(audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1, max_buffer_size_kb=100*1024):
    """
    Returns a list of all silent sections [start, end] in milliseconds of audio_segment.
    Inverse of detect_nonsilent().

    audio_segment - the segment to find silence in
    min_silence_len - the minimum length for any silent section
    silence_thresh - the upper bound for how quiet is silent in dFBS
    seek_step - step size for interating over the segment in ms
    max_buffer_size_kb - the maximum size of internally allocated buffers in KiB
    """
    raw_data = _convert_to_numpy(audio_segment)
    min_silence_ms = min_silence_len
    silence_threshold_db = silence_thresh
    seek_step_ms = seek_step
    
    seg_len_ms = len(audio_segment)
    frames_per_ms = audio_segment.frame_rate / 1000
    
    assert raw_data.shape[0] == audio_segment.frame_count()
    assert raw_data.shape[1] == audio_segment.channels
    
    max_frames_in_slice = int(np.ceil(min_silence_ms * frames_per_ms))
    
    # determine number of frames in computation window buffer
    if max_buffer_size_kb >= 0:
        bytes_per_frame = 8
        frames_per_kb = 1024 // bytes_per_frame
        buffer_len = max_buffer_size_kb * frames_per_kb
        # empirical testing shows that we need approximately 4 times as much memory
        # as buffer_len would suggest, probably because numpy allocates additional buffers
        # in the background during computations; we correct for this by adjusting buffer_len accordingly
        correction_constant = 4
        buffer_len //= correction_constant
        if buffer_len < max_frames_in_slice:
            min_buffer_size = int(np.ceil(max_frames_in_slice * bytes_per_frame / 1024)) * correction_constant
            raise ValueError("Buffer is too small, must be at least {} for the given {}" % min_buffer_size, min_silence_ms)
    else:
        buffer_len = len(raw_data)  # no restrictions!
        
    
    # you can't have a silent portion of a sound that is longer than the sound
    if seg_len_ms < min_silence_ms:
        return []
    
    # convert silence threshold to a float value (so we can compare it to rms)
    normalization_const = float(audio_segment.max_possible_amplitude)
    # normalization_const = 1.
    silence_thresh = db_to_float(silence_threshold_db) * audio_segment.max_possible_amplitude / normalization_const

    # check successive (1 sec by default) chunk of sound for silence
    # try a chunk at every "seek step" (or every chunk for a seek step == 1)
    last_slice_start = seg_len_ms - min_silence_ms
    slice_starts = range(0, last_slice_start + 1, seek_step_ms)

    # guarantee last_slice_start is included in the range
    # to make sure the last portion of the audio is searched
    if last_slice_start % seek_step_ms:
        slice_starts = itertools.chain(slice_starts, [last_slice_start])

    # list of all continuous regions of silence (start ms - end ms)
    silent_ranges = []
    
    prev_silent_ms = None
    current_range_start = None

    # load first window into buffer
    # the cumsq_per_frame buffer holds the cumulative sum of means of squares over channels for each frame,
    # normalized by max_possible_amplitude (i.e., all possible values x are 0 <= x <= 1) - this is
    # to prevent cumulative sums of square from exceeding representable values
    cumsq_per_frame = np.concatenate((
        [0.],
        np.cumsum(
            np.mean((raw_data[0:buffer_len].astype(np.float64))**2, axis=-1)
            / (normalization_const**2)
        )
    ))
    # keep track of the frames currently in the buffer
    buffer_offset = 0
    buffer_end = buffer_len
    
    for slice_start_ms in slice_starts:
        slice_start = int(slice_start_ms * frames_per_ms)
        slice_end = min(int((slice_start_ms + min_silence_ms) * frames_per_ms), len(raw_data))
        assert slice_end <= len(raw_data)
        # if the frame_rate is not divisible by min_silence_ms, we may have frames with slightly varying lengths
        # so we compute the actual length of the concrete slice here
        frames_in_slice = slice_end - slice_start
        
        if slice_end > buffer_end: # we ran out of buffer; load next window into buffer           
            cumsq_per_frame = np.concatenate((
                [0.],
                np.cumsum(
                    np.mean(
                        (raw_data[slice_start:slice_start + buffer_len].astype(np.float64))**2,
                        axis=-1
                    ) / (normalization_const**2)
                )
                
            ))
            buffer_offset = slice_start
            buffer_end = buffer_offset + buffer_len
            
        # compute the RMS for the current slice from the cumulative sums of squares in the buffer
        slice_msq = cumsq_per_frame[slice_end - buffer_offset] - cumsq_per_frame[slice_start - buffer_offset]
        rms = np.sqrt(slice_msq / frames_in_slice)

        if rms <= silence_thresh:
            # silence_starts.append(slice_start_ms) 
            # current slice is silent; combine with preceeding silent slice if no nonsilent gap
            if current_range_start is None:
                current_range_start = slice_start_ms
            else:
                continuous = (slice_start_ms == prev_silent_ms + seek_step)
                
                # sometimes two small blips are enough for one particular slice to be
                # non-silent, despite the silence all running together. Just combine
                # the two overlapping silent ranges.
                silence_has_gap = slice_start_ms > (prev_silent_ms + min_silence_len)

                if not continuous and silence_has_gap:
                    silent_ranges.append([
                        current_range_start,
                        prev_silent_ms + min_silence_len
                    ])
                    current_range_start = slice_start_ms
                    
            prev_silent_ms = slice_start_ms
            
    if current_range_start is not None:
        assert prev_silent_ms is not None
        silent_ranges.append([current_range_start,
                              prev_silent_ms + min_silence_len])

    return silent_ranges


def detect_nonsilent(audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1):
    """
    Returns a list of all nonsilent sections [start, end] in milliseconds of audio_segment.
    Inverse of detect_silent()

    audio_segment - the segment to find silence in
    min_silence_len - the minimum length for any silent section
    silence_thresh - the upper bound for how quiet is silent in dFBS
    seek_step - step size for interating over the segment in ms
    """
    silent_ranges = detect_silence(audio_segment, min_silence_len, silence_thresh, seek_step)
    len_seg = len(audio_segment)

    # if there is no silence, the whole thing is nonsilent
    if not silent_ranges:
        return [[0, len_seg]]

    # short circuit when the whole audio segment is silent
    if silent_ranges[0][0] == 0 and silent_ranges[0][1] == len_seg:
        return []

    prev_end_i = 0
    nonsilent_ranges = []
    for start_i, end_i in silent_ranges:
        nonsilent_ranges.append([prev_end_i, start_i])
        prev_end_i = end_i

    if end_i != len_seg:
        nonsilent_ranges.append([prev_end_i, len_seg])

    if nonsilent_ranges[0] == [0, 0]:
        nonsilent_ranges.pop(0)

    return nonsilent_ranges


def split_on_silence(audio_segment, min_silence_len=1000, silence_thresh=-16, keep_silence=100,
                     seek_step=1):
    """
    Returns list of audio segments from splitting audio_segment on silent sections

    audio_segment - original pydub.AudioSegment() object

    min_silence_len - (in ms) minimum length of a silence to be used for
        a split. default: 1000ms

    silence_thresh - (in dBFS) anything quieter than this will be
        considered silence. default: -16dBFS

    keep_silence - (in ms or True/False) leave some silence at the beginning
        and end of the chunks. Keeps the sound from sounding like it
        is abruptly cut off.
        When the length of the silence is less than the keep_silence duration
        it is split evenly between the preceding and following non-silent
        segments.
        If True is specified, all the silence is kept, if False none is kept.
        default: 100ms

    seek_step - step size for interating over the segment in ms
    """

    # from the itertools documentation
    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    if isinstance(keep_silence, bool):
        keep_silence = len(audio_segment) if keep_silence else 0

    output_ranges = [
        [ start - keep_silence, end + keep_silence ]
        for (start,end)
            in detect_nonsilent(audio_segment, min_silence_len, silence_thresh, seek_step)
    ]

    for range_i, range_ii in pairwise(output_ranges):
        last_end = range_i[1]
        next_start = range_ii[0]
        if next_start < last_end:
            range_i[1] = (last_end+next_start)//2
            range_ii[0] = range_i[1]

    return [
        audio_segment[ max(start,0) : min(end,len(audio_segment)) ]
        for start,end in output_ranges
    ]


def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    """
    Returns the millisecond/index that the leading silence ends.

    audio_segment - the segment to find silence in
    silence_threshold - the upper bound for how quiet is silent in dFBS
    chunk_size - chunk size for interating over the segment in ms
    """
    trim_ms = 0 # ms
    assert chunk_size > 0 # to avoid infinite loop
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    # if there is no end it should return the length of the segment
    return min(trim_ms, len(sound))


