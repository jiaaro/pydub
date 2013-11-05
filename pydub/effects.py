from .utils import (
    db_to_float,
    ratio_to_db,
    register_pydub_effect,
    make_chunks,
)
from .exceptions import TooManyMissingFrames


@register_pydub_effect
def normalize(seg, headroom=0.1):
    """
    headroom is how close to the maximum volume to boost the signal up to (specified in dB)
    """
    peak_sample_val = seg.max
    target_peak = seg.max_possible_amplitude * db_to_float(-headroom)

    needed_boost = ratio_to_db(target_peak / peak_sample_val)
    return seg.apply_gain(needed_boost)


@register_pydub_effect
def speedup(seg, playback_speed=1.5, chunk_size=150, crossfade=25):
    # we will keep audio in 150ms chunks since one waveform at 20Hz is 50ms long
    # (20 Hz is the lowest frequency audible to humans)

    # portion of AUDIO TO KEEP. if playback speed is 1.25 we keep 80% (0.8) and
    # discard 20% (0.2)
    atk = 1.0 / playback_speed

    if playback_speed < 2.0:
        # throwing out more than half the audio - keep 50ms chunks
        ms_to_remove_per_chunk = int(chunk_size * (1 - atk) / atk)
    else:
        # throwing out less than half the audio - throw out 50ms chunks
        ms_to_remove_per_chunk = int(chunk_size)
        chunk_size = int(atk * chunk_size / (1 - atk))

    # the crossfade cannot be longer than the amount of audio we're removing
    crossfade = min(crossfade, ms_to_remove_per_chunk - 1)

    # DEBUG
    #print("chunk: {0}, rm: {1}".format(chunk_size, ms_to_remove_per_chunk))

    chunks = make_chunks(seg, chunk_size + ms_to_remove_per_chunk)
    if len(chunks) < 2:
        raise Exception("Could not speed up AudioSegment, it was too short {2:0.2f}s for the current settings:\n{0}ms chunks at {1:0.1f}x speedup".format(
            chunk_size, playback_speed, seg.duration_seconds))

    # we'll actually truncate a bit less than we calculated to make up for the
    # crossfade between chunks
    ms_to_remove_per_chunk -= crossfade

    # we don't want to truncate the last chunk since it is not guaranteed to be
    # the full chunk length
    last_chunk = chunks[-1]
    chunks = [chunk[:-ms_to_remove_per_chunk] for chunk in chunks[:-1]]

    out = chunks[0]
    for chunk in chunks[1:]:
        out = out.append(chunk, crossfade=crossfade)

    out += last_chunk
    return out
    
@register_pydub_effect
def strip_silence(seg, silence_len=1000, silence_thresh=-20):
    silence_thresh = seg.rms * db_to_float(silence_thresh)
    
    # find silence and add start and end indicies to the to_cut list
    to_cut = []
    silence_start = None
    for i, sample in enumerate(seg):
        if sample.rms < silence_thresh:
            if silence_start is None:
                silence_start = i
            continue
            
        if silence_start is None:
            continue
            
        if i - silence_start > silence_len:
            to_cut.append([silence_start, i-1])
        
        silence_start = None
            
    # print(to_cut)
    
    keep_silence = 100
    
    to_cut.reverse()
    for cstart, cend in to_cut:
        if len(seg[cend:]) < keep_silence:
            seg = seg[:cstart + keep_silence]
        elif len(seg[:cstart]) < keep_silence:
            seg = seg[cend-keep_silence:]
        else:
            #print(cstart, "-", cend)
            seg = seg[:cstart+keep_silence].append(seg[cend-keep_silence:], crossfade=keep_silence*2)
    return seg