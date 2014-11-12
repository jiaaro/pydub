# API Documentation

This document is a work in progress.

If you're looking for some functionality in particular, it is a *very* good idea to take a look at the [source code](https://github.com/jiaaro/pydub). Core functionality is mostly in `pydub/audio_segment.py` – a number of `AudioSegment` methods are in the `pydub/effects.py` module, and added to `AudioSegment` via the effect registration process (the `register_pydub_effect()` decorator function)

## AudioSegment()

`AudioSegment` objects are immutable, and support a number of operators.

```python
from pydub import AudioSegment
sound1 = AudioSegment.from_file("/path/to/sound.wav", format="wav")
sound2 = AudioSegment.from_file("/path/to/another_sound.wav", format="wav")

# sound1 6 dB louder, then 3.5 dB quieter
louder = sound1 + 6
quieter = sound1 - 3.5

# sound1, with sound2 appended
combined = sound1 + sound2

# sound1 repeated 3 times
repeated = sound1 * 3

# duration
duration_in_milliseconds = len(sound1)

# first 5 seconds of sound1
beginning = sound1[:5000]

# last 5 seconds of sound1
end = sound1[-5000:]
```

### AudioSegment(…).export()

Write the `AudioSegment` object to a file – returns a file handle of the output file (you don't have to do anything with it, though).

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("/path/to/sound.wav", format="wav")

file_handle = sound.export("/path/to/output.mp3", format="mp3")
mp3_file = sound.export(tags={"album": "The Bends", "artist": "Radiohead"}, bitrate="192k")
```

No arguments are required. 

The first agument is the location (as a string) to write the output, **or** a file handle to write to. If you do not pass an output file or path, a temporary file is generated.

**Supported keyword arguments**:

- `format` | example: `"aif"` | default: `"mp3"`  
  Format of the output file, supports `"wav"` natively, requires ffmpeg for all other formats.
- `bitrate` | example: `"128k"`  
  For compressed formats, you can pass the bitrate you'd like the encoder to use (requires ffmpeg)
- `tags` | example: `{"album": "1989", "artist": "Taylor Swift"}`  
  Allows you to supply media info tags for the encoder (requires ffmpeg). Not all formats can receive tags (mp3 can).
- `parameters` | example: `["-ac", "2"]`  
  Pass additional [commpand line parameters](https://www.ffmpeg.org/ffmpeg.html) to the ffmpeg call. These are added to the end of the call (in the output file section).

### AudioSegment.empty()

Creates a zero-duration `AudioSegment`.

```python
from pydub import AudioSegment
empty = AudioSegment.empty()

len(empty) == 0
```

This is useful for aggregation loops:
```python
from pydub import AudioSegment

sounds = [
  AudioSegment.from_wav("sound1.wav"), 
  AudioSegment.from_wav("sound2.wav"), 
  AudioSegment.from_wav("sound3.wav"), 
]

playlist = AudioSegment.empty()
for sound in sounds:
  playlist += sound
```

### AudioSegment.silent()

Creates a silent audiosegment, which can be used as a placeholder, spacer, or as a canvas to overlay other sounds on top of.

```python
from pydub import AudioSegment

ten_second_silence = AudioSegment.silent(duration=10000)
```

**Supported keyword arguments**:

- `duration` | example: `3000` | default: `1000` (1 second)  
  Length of the silent `AudioSegment`, in milliseconds

### AudioSegment(…).dBFS

Returns the loudness of the `AudioSegment` in dBFS (db relative to the maximum possible loudness). A Square wave at maximum amplitude will be roughly 0 dBFS (maximum loudness), whereas a Sine Wave at maximum amplitude will be roughly -3 dBFS.

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

loudness = sound.dBFS
```

### AudioSegment(…).channels

Number of channels in this audio segment (1 means mono, 2 means stereo)

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

channel_count = sound.channels
```

### AudioSegment(…).sample_width

Number of bytes in each sample (1 means 8 bit, 2 means 16 bit, etc). CD Audio is 16 bit, (sample width of 2 bytes).

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

bytes_per_sample = sound.sample_width
```

### AudioSegment(…).frame_rate

CD Audio has a 44.1kHz sample rate, which means `frame_rate` will be `44100` (same as sample rate, see `frame_width`). Common values are `44100` (CD), `48000` (DVD), `22050`, `24000`, `12000` and `11025`.

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

frames_per_second = sound.frame_rate
```

### AudioSegment(…).frame_width

Number of bytes for each "frame". A frame contains a sample for each channel (so for stereo you have 2 samples per frame, which are played simultaneously). `frame_width` is equal to `channels * sample_width`. For CD Audio it'll be `4` (2 channels times 2 bytes per sample).

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

bytes_per_frame = sound.frame_width
```

### AudioSegment(…).rms

A measure of loudness. Used to compute dBFS, which is what you should use in most cases. Loudness is logarithmic (rms is not), which makes dB a much more natural scale.

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

loudness = sound.rms
```

### AudioSegment(…).max

The highest amplitude of any sample in the `AudioSegment`. Useful for things like normalization (which is provided in `pydub.effects.normalize`).

```python
from pydub import AudioSegment
sound = AudioSegment.from_file("sound1.wav")

peak_amplitude = sound.max
```

### AudioSegment(…).frame_count()
### AudioSegment(…).set_sample_width()
### AudioSegment(…).set_frame_rate()
### AudioSegment(…).set_channels()
### AudioSegment(…).duration_seconds
### AudioSegment(…).apply_gain()
### AudioSegment(…).overlay()
### AudioSegment(…).append()
### AudioSegment(…).fade()
### AudioSegment(…).fade_out()
### AudioSegment(…).fade_in()
### AudioSegment(…).reverse()
