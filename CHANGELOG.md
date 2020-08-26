# on master
- Don't show a runtime warning about the optional ffplay dependency being missing until someone trys to use it

# v0.24.1
- Fix bug where ffmpeg errors in Python 3 are illegible
- Fix bug where `split_on_silence` fails when there are one or fewer nonsilent segments
- Fix bug in fallback audioop implementation

# v0.24.0
- Fix inconsistent handling of 8-bit audio
- Fix bug where certain files will fail to parse
- Fix bug where pyaudio stream is not closed on error
- Allow codecs and parameters in wav and raw export
- Fix bug in `pydub.AudioSegment.from_file` where supplied codec is ignored
- Allow `pydub.silence.split_on_silence` to take a boolean for `keep_silence`
- Fix bug where `pydub.silence.split_on_silence` sometimes adds non-silence from adjacent segments
- Fix bug where `pydub.AudioSegment.extract_wav_headers` fails on empty wav files
- Add new function `pydub.silence.detect_leading_silence`
- Support conversion between an arbitrary number of channels and mono in `pydub.AudioSegment.set_channels`
- Fix several issues related to reading from filelike objects

# v0.23.1
- Fix bug in passing ffmpeg/avconv parameters for `pydub.AudioSegment.from_mp3()`, `pydub.AudioSegment.from_flv()`, `pydub.AudioSegment.from_ogg()`, and `pydub.AudioSegment.from_wav()`
- Fix logic bug in `pydub.effects.strip_silence()`

# v0.23.0
- Add support for playback via simpleaudio
- Allow users to override the type in `pydub.AudioSegment().get_array_of_samples()` (PR #313)
- Fix a bug where the wrong codec was used for 8-bit audio (PR #309 - issue #308)

# v0.22.1
- Fix `pydub.utils.mediainfo_json()` to work with newer, backwards-incompatible versions of ffprobe/avprobe

# v0.22.0
- Adds support for audio with frame rates (sample rates) of 48k and higher (requires scipy) (PR #262, fixes #134, #237, #209)
- Adds support for PEP 519 File Path protocol (PR #252)
- Fixes a few places where handles to temporary files are kept open (PR #280)
- Add the license file to the python package to aid other packaging projects (PR #279, fixes #274)
- Big fix for `pydub.silence.detect_silence()` (PR #263)

# v0.21.0
- NOTE: Semi-counterintuitive change: using the a stride when slicing AudioSegment instances (for example, `sound[::5000]`) will return chunks of 5000ms (not 1ms chunks every 5000ms) (#222)
- Debug output from ffmpeg/avlib is no longer printed to the console unless you set up logging (see README for how to set up logging for your converter) (#223)
- All pydub exceptions are now subclasses of `pydub.exceptions.PydubException` (PR #244)
- The utilities in `pydub.silence` now accept a `seek_step`argument which can optionally be passed to improve the performance of silence detection (#211)
- Fix to `pydub.silence` utilities which allow you to detect perfect silence (#233)
- Fix a bug where threaded code screws up your terminal session due to ffmpeg inheriting the stdin from the parent process. (#231)
- Fix a bug where a crashing programs using pydub would leave behind their temporary files (#206)

# v0.20.0
- Add new parameter `gain_during_overlay` to `pydub.AudioSegment.overlay` which allows users to adjust the volume of the target AudioSegment during the portion of the segment which is overlaid with the additional AudioSegment.
- `pydub.playback.play()` No longer displays the (very verbose) playback "banner" when using ffplay
- Fix a confusing error message when using invalid crossfade durations (issue #193)

# v0.19.0
- Allow codec and ffmpeg/avconv parameters to be set in the `pydub.AudioSegment.from_file()` for more control while decoding audio files
- Allow `AudioSegment` objects with more than two channels to be split using `pydub.AudioSegment().split_to_mono()`
- Add support for inverting the phase of only one channel in a multi-channel `pydub.AudioSegment` object
- Fix a bug with the latest avprobe that broke `pydub.utils.mediainfo()`
- Add tests for webm encoding/decoding

# v0.18.0
- Add a new constructor: `pydub.AudioSegment.from_mono_audiosegments()` which allows users to create a multi-channel audiosegment out of multiple mono ones.
- Refactor `pydub.AudioSegment._sync()` to support an arbitrary number of audiosegment arguments.

# v0.17.0
- Add the ability to add a cover image to MP3 exports via the `cover` keyword argument to `pydub.AudioSegment().export()`
- Add `pydub.AudioSegment().get_dc_offset()` and `pydub.AudioSegment().remove_dc_offset()` which allow detection and removal of DC offset in audio files.
- Minor fixes for windows users

# v0.16.7
- Make `pydub.AudioSegment()._spawn()` accept array.array instances containing audio samples

# v0.16.6
- Make `pydub.AudioSegment()` objects playable inline in ipython notebooks.
- Add scipy powered high pass, low pass, and band pass filters, which can be high order filters (they take `order` as a keyword argument). They are used for `pydub.AudioSegment().high_pass_filter()`, `pydub.AudioSegment().low_pass_filter()`, `pydub.AudioSegment().band_pass_filter()` when the `pydub.scipy_effects` module is imported.
- Fix minor bug in `pydub.silence.detect_silence()`

# v0.16.5
- Update `pydub.AudioSegment()._spawn()` method to allow user subclassing of `pydub.AudioSegment`
- Add a workaround for incorrect duration reporting of some mp3 files on macOS

# v0.16.4
- Add support for radd (basically, allow `sum()` to operate on an iterable of `pydub.AudioSegment()` objects)
- Fix bug in 24-bit wav support (understatement. It didn't work right at all the first time)

# v0.16.3
- Add support for python 3.5 (overstatement. We just added python 3.5 to CI and it worked 😄)
- Add native support for 24-bit wav files (ffmpeg/avconv not required)

# v0.16.2
- Fix bug where you couldn't directly instantiate `pydub.AudioSegment` with `bytes` data in python 3

# v0.16.1
- pydub will use any ffmpeg/avconv binary that's in the current directory (as reported by `os.getcwd()`) before searching for a system install

# v0.16.0
- Make it easier to instantiate `pydub.AudioSegment()` directly when creating audio segments from raw audio data (without having to write it to a file first)
- Add `pydub.AudioSegment().get_array_of_samples()` method which returns the samples which make up an audio segment (you should usually prefer this over `pydub.AudioSegment().raw_data`)
- Add `pydub.AudioSegment().raw_data` property which returns the raw audio data for an audio segment as a bytes (python 3) or a bytestring (python 3)
- Allow users to specify frame rate in `pydub.AudioSegment.silent()` constructor

# v0.15.0
- Add support for RAW audio (basically WAV format, but without wave headers)
- Add a new exception `pydub.exceptions.CouldntDecodeError` to indicate a failure of ffmpeg/avconv to decode a file (as indicated by ffmpeg/avconv exit code)

# v0.14.2
- Fix a bug in python 3.4 which failed to read wave files with no audio data (should have been audio segments with a duration of 0 ms)

# v0.14.1
- Fix a bug in `pydub.utils.mediainfo()` that caused inputs containing unescaped characters to raise a runtime error (inputs are not supposed to require escaping)

# v0.14.0
- Rename `pydub.AudioSegment().set_gain()` to `pydub.AudioSegment().apply_gain_stereo()` to better reflect it's place in the world (as a counterpart to `pydub.AudioSegment().apply_gain()`)

# v0.13.0
- Add `pydub.AudioSegment().pan()` which returns a new stereo audio segment panned left/right as specified.

# v0.12.0
- Add a logger, `"pydub.converter"` which logs the ffmpeg commands being run by pydub.
- Add `pydub.AudioSegment().split_to_mono()` method which returns a list of mono audio segments. One for each channel in the original audio segment.
- Fix a bug in `pydub.silence.detect_silence()` which caused the function to break when a silent audio segment was equal in length to the minimum silence length. It should report a single span of silence covering the whole silent audio segment. Now it does.
- Fix a bug where uncommon wav formats (those not supported by the stdlib wave module) would throw an exception rather than converting to a more common format via ffmpeg/avconv

# v0.11.0
- Add `pydub.AudioSegment().max_dBFS` which reports the loudness (in dBFS) of the loudest point (i.e., highest amplitude sample) of an audio segment

# v0.10.0
- Overhaul Documentation
- Improve performance of `pydub.AudioSegment().overlay()`
- Add `pydub.AudioSegment().invert_phase()` which (shocker) inverts the phase of an audio segment
- Fix a type error in `pydub.AudioSegment.get_sample_slice()`

# v0.9.5
- Add `pydub.generators` module containing simple signal generation functions (white noise, sine, square wave, etc)
- Add a `loops` keyword argument to `pydub.AudioSegment().overlay()` which allows users to specify that the overlaid audio should be repeated (i.e., looped) a certain number of times, or indefinitely

# 0.9.4
- Fix a bug in db_to_float() where all values were off by a factor of 2

# 0.9.3
- Allow users to set the location of their converter by setting `pydub.AudioSegment.converter = "/path/to/ffmpeg"` and added a shim to support the old method of assigning to `pydub.AudioSegment.ffmpeg` (which is deprecated now that we support avconv)

# v0.9.2
- Add support for Python 3.4
- Audio files opened with format "wave" are treated as "wav" and "m4a" are treated as "mp4"
- Add `pydub.silence` module with simple utilities for detecting and removing silence.
- Fix a bug affecting auto-detection of ffmpeg/avconv on windows.
- Fix a bug that caused pydub to only work when ffmpeg/avconv is present (it should be able to work with WAV data without any dependencies)

# v0.9.1
- Add a runtime warning when ffmpeg/avconv cannot be found to aid debugging

# v0.9.0
- Added support for pypy (by reimplementing audioop in python). Also, we contributed our implementation to the pypy project, so that's 💯
- Add support for avconv as an alternative to ffmpeg
- Add a new helper module `pydub.playback` which allows you to quickly listen to an audio segment using ffplay (or avplay)
- Add new function `pydub.utils.mediainfo('/path/to/audio/file.ext')` which reports back the results of ffprobe (or avprobe) including codec, bitrate, channels, etc
