# API Documentation

This document is a work in progress

## AudioSegment()

`AudioSegment` objects are immutable, and support a number of operators.

```python
from pydub import AudioSegment
sound1 = AudioSegment.from_file("/path/to/sound.wav", format="wav")
sound2 = AudioSegment.from_file("/path/to/another_sound.wav", format="wav")

# sound1 6 dB louder, then 3.5 dB quieter
louder = sound1 + 6
quieter = sound1 - 3.5

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
```

No arguments are required. 

The first agument is the location (as a string) to write the output, **or** a file handle to write to. If you do not pass an output file or path, a temporary file is generated.

**Supported keyword arguments**:

- `format` – example: `"aif"` – Format of the output file, supports `"wav"` natively, requires ffmpeg for all other formats.
- `bitrate` – example: `"128k" – for compressed formats, you can pass the bitrate you'd like the encoder to use (requires ffmpeg)
- `tags` - example: `{"album": "1989", "artist": "Taylor Swift"}` – Allows you to supply media info tags for the encoder (requires ffmpeg). Not all formats can receive tags (mp3 can).
- `parameters` – example: `["-ac", "2"]` – Pass additional [commpand line parameters](https://www.ffmpeg.org/ffmpeg.html) to the ffmpeg call. These are added to the end of the call (in the output file section).

