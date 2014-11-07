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
