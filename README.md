# Pydub [![Build Status](https://travis-ci.org/jiaaro/pydub.svg?branch=master)](https://travis-ci.org/jiaaro/pydub) [![Build status](https://ci.appveyor.com/api/projects/status/gy1ucp9o5khq7fqi/branch/master?svg=true)](https://ci.appveyor.com/project/jiaaro/pydub/branch/master)

Pydub lets you do stuff to audio in a way that isn't stupid.

**Stuff you might be looking for**:
 - [Installing Pydub](https://github.com/jiaaro/pydub#installation)
 - [API Documentation](https://github.com/jiaaro/pydub/blob/master/API.markdown)
 - [Dependencies](https://github.com/jiaaro/pydub#dependencies)
 - [Playback](https://github.com/jiaaro/pydub#playback)
 - [Setting up ffmpeg](https://github.com/jiaaro/pydub#getting-ffmpeg-set-up)
 - [Questions/Bugs](https://github.com/jiaaro/pydub#bugs--questions)
 

##  Quickstart

Open a WAV file

```python
from pydub import AudioSegment

song = AudioSegment.from_wav("never_gonna_give_you_up.wav")
```

...or a mp3

```python
song = AudioSegment.from_mp3("never_gonna_give_you_up.mp3")
```

... or an ogg, or flv, or [anything else ffmpeg supports](http://www.ffmpeg.org/general.html#File-Formats)

```python
ogg_version = AudioSegment.from_ogg("never_gonna_give_you_up.ogg")
flv_version = AudioSegment.from_flv("never_gonna_give_you_up.flv")

mp4_version = AudioSegment.from_file("never_gonna_give_you_up.mp4", "mp4")
wma_version = AudioSegment.from_file("never_gonna_give_you_up.wma", "wma")
aac_version = AudioSegment.from_file("never_gonna_give_you_up.aiff", "aac")
```

Slice audio:

```python
# pydub does things in milliseconds
ten_seconds = 10 * 1000

first_10_seconds = song[:ten_seconds]

last_5_seconds = song[-5000:]
```

Make the beginning louder and the end quieter

```python
# boost volume by 6dB
beginning = first_10_seconds + 6

# reduce volume by 3dB
end = last_5_seconds - 3
```

Concatenate audio (add one file to the end of another)

```python
without_the_middle = beginning + end
```

How long is it?

```python
without_the_middle.duration_seconds == 15.0
```

AudioSegments are immutable

```python
# song is not modified
backwards = song.reverse()
```

Crossfade (again, beginning and end are not modified)

```python
# 1.5 second crossfade
with_style = beginning.append(end, crossfade=1500)
```

Repeat

```python
# repeat the clip twice
do_it_over = with_style * 2
```

Fade (note that you can chain operations because everything returns
an AudioSegment)

```python
# 2 sec fade in, 3 sec fade out
awesome = do_it_over.fade_in(2000).fade_out(3000)
```

Save the results (again whatever ffmpeg supports)

```python
awesome.export("mashup.mp3", format="mp3")
```

Save the results with tags (metadata)

```python
awesome.export("mashup.mp3", format="mp3", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})
```

You can pass an optional bitrate argument to export using any syntax ffmpeg 
supports.

```python
awesome.export("mashup.mp3", format="mp3", bitrate="192k")
```

Any further arguments supported by ffmpeg can be passed as a list in a 
'parameters' argument, with switch first, argument second. Note that no 
validation takes place on these parameters, and you may be limited by what 
your particular build of ffmpeg/avlib supports.

```python
# Use preset mp3 quality 0 (equivalent to lame V0)
awesome.export("mashup.mp3", format="mp3", parameters=["-q:a", "0"])

# Mix down to two channels and set hard output volume
awesome.export("mashup.mp3", format="mp3", parameters=["-ac", "2", "-vol", "150"])
```

## Debugging

Most issues people run into are related to converting between formats using
ffmpeg/avlib. Pydub provides a logger that outputs the subprocess calls to 
help you track down issues:

```python
>>> import logging

>>> l = logging.getLogger("pydub.converter")
>>> l.setLevel(logging.DEBUG)
>>> l.addHandler(logging.StreamHandler())

>>> AudioSegment.from_file("./test/data/test1.mp3")
subprocess.call(['ffmpeg', '-y', '-i', '/var/folders/71/42k8g72x4pq09tfp920d033r0000gn/T/tmpeZTgMy', '-vn', '-f', 'wav', '/var/folders/71/42k8g72x4pq09tfp920d033r0000gn/T/tmpK5aLcZ'])
<pydub.audio_segment.AudioSegment object at 0x101b43e10>
```

Don't worry about the temporary files used in the conversion. They're cleaned up 
automatically.

## Bugs & Questions

You can file bugs in our [github issues tracker](https://github.com/jiaaro/pydub/issues), 
and ask any technical questions on 
[Stack Overflow using the pydub tag](http://stackoverflow.com/questions/ask?tags=pydub). 
We keep an eye on both.

## Installation

Installing pydub is easy, but don't forget to install ffmpeg/avlib (the next section in this doc)

    pip install pydub

Or install the latest dev version from github (or replace `@master` with a [release version like `@v0.12.0`](https://github.com/jiaaro/pydub/releases))…

    pip install git+https://github.com/jiaaro/pydub.git@master

-OR-

    git clone https://github.com/jiaaro/pydub.git

-OR-

Copy the pydub directory into your python path. Zip 
[here](https://github.com/jiaaro/pydub/zipball/master)

## Dependencies

You can open and save WAV files with pure python. For opening and saving non-wav 
files – like mp3 – you'll need [ffmpeg](http://www.ffmpeg.org/) or 
[libav](http://libav.org/).

### Playback

You can play audio if you have one of these installed (simpleaudio _strongly_ recommended, even if you are installing ffmpeg/libav):

 - [simpleaudio](https://simpleaudio.readthedocs.io/en/latest/)
 - [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/docs/#)
 - ffplay (usually bundled with ffmpeg, see the next section)
 - avplay (usually bundled with libav, see the next section)
 
```python
from pydub import AudioSegment
from pydub.playback import play

sound = AudioSegment.from_file("mysound.wav", format="wav")
play(sound)
```

## Getting ffmpeg set up

You may use **libav or ffmpeg**.

Mac (using [homebrew](http://brew.sh)):

```bash
# libav
brew install libav --with-libvorbis --with-sdl --with-theora

####    OR    #####

# ffmpeg
brew install ffmpeg --with-libvorbis --with-sdl2 --with-theora
```

Linux (using aptitude):

```bash
# libav
apt-get install libav-tools libavcodec-extra

####    OR    #####

# ffmpeg
apt-get install ffmpeg libavcodec-extra
```

Windows:

1. Download and extract libav from [Windows binaries provided here](http://builds.libav.org/windows/).
2. Add the libav `/bin` folder to your PATH envvar
3. `pip install pydub`

## Important Notes

`AudioSegment` objects are [immutable](http://www.devshed.com/c/a/Python/String-and-List-Python-Object-Types/1/)


### Ogg exporting and default codecs

The Ogg specification ([http://tools.ietf.org/html/rfc5334](rfc5334)) does not specify
the codec to use, this choice is left up to the user. Vorbis and Theora are just
some of a number of potential codecs (see page 3 of the rfc) that can be used for the
encapsulated data.

When no codec is specified exporting to `ogg` will _default_ to using `vorbis`
as a convinence. That is:

```python
from pydub import AudioSegment
song = AudioSegment.from_mp3("test/data/test1.mp3")
song.export("out.ogg", format="ogg")  # Is the same as:
song.export("out.ogg", format="ogg", codec="libvorbis")
```

## Example Use

Suppose you have a directory filled with *mp4* and *flv* videos and you want to convert all of them to *mp3* so you can listen to  them on your mp3 player.

```python
import os
import glob
from pydub import AudioSegment

video_dir = '/home/johndoe/downloaded_videos/'  # Path where the videos are located
extension_list = ('*.mp4', '*.flv')

os.chdir(video_dir)
for extension in extension_list:
    for video in glob.glob(extension):
        mp3_filename = os.path.splitext(os.path.basename(video))[0] + '.mp3'
        AudioSegment.from_file(video).export(mp3_filename, format='mp3')
```

### Batch Conversion

Any local, conventional music archive (that is, with lossless compressed or uncompressed files) very quickly grows too large for mobile devices.
To have the entire personal music collection on a phone requires some converting.
This is easily done, but this script is a bit smarter about it and skips existing files and just copies over already existing `mp3`s, among other things.
It also preserves most/all metadata, something [`ffmpeg` does by default](https://stackoverflow.com/questions/26109837/convert-flac-to-mp3-with-ffmpeg-keeping-all-metadata#comment68867375_26109838) but `pydub` apparently struggles with (per default at least).

The user can give a list of file formats that are to be converted, *e.g.* `flac`, `wav`, ...

The target file format aka extension is also hard-coded into the script, not that it matters.
Currently, this is `mp3` at the default bitrate of 128k.
That seems pretty low, but gives nice and compact files; chances are the difference will never be relevant on mobile headphones, especially in-ears.
For more info, [see here](https://github.com/alexpovel/random_python/tree/master/flac-collection_to_mobile).

```python
#!/usr/bin/env python3

import logging
import sys
from pathlib import Path
from shutil import copy2 as copy  # copy2 also copies metadata

import fleep  # get file type from binary header
from pydub import AudioSegment  # just a wrapper for ffmpeg
from pydub.utils import mediainfo  # metadata utility


logging.basicConfig(
    filename="output.log",
    filemode="w",  # over_w_rite file each time
    level=logging.INFO,  # Only print this level and above
    format="[%(asctime)s] "\
    "%(levelname)s (%(lineno)d): %(message)s"  # Custom formatting
)


def read_bytes(file, no_of_bytes=128):
    """
    Open the file in bytes mode, read it, and close the file.
    This is a blatant copy of the existing pathlib Path class method
    of the same name, which doesn't offer an argument for the
    amount of bytes to read.
    According to fleep documentation, first 128 bytes is enough to
    determine the file type from the binary file header.
    """
    with file.open(mode='rb') as f:
        return f.read(no_of_bytes)


def fleepget(item):
    return fleep.get(read_bytes(item))


def copy_if_not_exist(src, dest):
    if not dest.is_file():
        copy(src, dest)  # Copy over as-is
        logging.info(f"\t\tCopying succeeded.")
    else:
        logging.info(f"\t\tCopying did not succeed: target existed.")


paths = {
    "import": {
        "root": Path.home() / "Music"
    },
    "export": {}
}

# Provide ability to get path from command line argument
try:
    paths["export"]["root"] = Path(sys.argv[1])
except IndexError:
    paths["export"]["root"] = Path.home() / "Music_Export"

paths["export"]["root"].mkdir(exist_ok=True)

extensions = {
    "to_convert": ["flac"],
    # ogg/vorbis would be preferred but mp3 has better (mobile) support
    "target": "mp3"
}
logging.info(f"Extensions to be converted are: {extensions['to_convert']}")
logging.info(f"They are going to be converted to: {extensions['target']}")


# Visit all subdirectories recurvisely.
for item in paths["import"]["root"].rglob("*"):

    # Mirror found directory structure relative to the import root directory
    # over to the export directory, also relative.
    paths["export"]["relative"] = item.relative_to(paths["import"]["root"])

    paths["export"]["full"] = paths["export"]["root"].joinpath(
        paths["export"]["relative"])

    if item.is_dir():
        paths["export"]["full"].mkdir(parents=True, exist_ok=True)
        logging.info(f"Created directory: {paths['export']['full']}")

    if not item.is_file():
        continue
    logging.info(f"Found file to be processed: {item}")

    fileheader = fleepget(item)  # Binary file header with file metainfo

    if fileheader.type_matches("audio"):
        logging.info("\tDetected an audio file.")
        # File extension we're dealing with (returned without leading period).
        ext = fileheader.extension[0].lower()

        if ext in extensions["to_convert"]:
            logging.info(
                f"\tAudio file extension '{ext}' belongs to list of conversion candidates, starting conversion:")
            # The new file, which differs from the 'full' file by its suffix.
            # Change extension, else we get e.g. "file.flac" when it's actually an mp3.
            paths["export"]["new"] = paths["export"]["full"].with_suffix(
                "." + extensions["target"])
            logging.info(f"\t\tTarget audio file is: {paths['export']['new']}")

            if not paths["export"]["new"].is_file():
                AudioSegment.from_file(item).export(
                    paths["export"]["new"],
                    format=extensions["target"],
                    # Copy over metadata.
                    # ffmpeg does this automatically without 'map_metadata' nowadays,
                    # but even with "-map_metadata 0" as the value to the "parameters" key,
                    # this doesn't work for PyDub.
                    # Return empty dict if key not found.
                    tags=mediainfo(item).get("TAG", {}),
                    # bitrate="320k", # 320k bitrate mp3 leads to large files
                    # parameters=["-map_metadata", "0"] # Use "tags" key above
                )
                logging.info("\t\tConversion succeeded.")
            else:
                logging.info("\t\tConversion did not succeed: target existed.")
        else:  # Audio file, but not to be converted.
            logging.info(
                f"\tAudio file is not a candidate for conversion, starting copy process to: {paths['export']['full']}")
            copy_if_not_exist(item, paths["export"]["full"])
    elif fileheader.type_matches("raster-image"):
        # Album covers (jpg, png, ...)
        logging.info(
            f"\tFile is a raster image (album art): {paths['export']['full']}")
        copy_if_not_exist(item, paths["export"]["full"])
    else:
        logging.warning(f"Item fell through (no criteria met): {item}")
```

### How about another example?

```python
from glob import glob
from pydub import AudioSegment

playlist_songs = [AudioSegment.from_mp3(mp3_file) for mp3_file in glob("*.mp3")]

first_song = playlist_songs.pop(0)

# let's just include the first 30 seconds of the first song (slicing
# is done by milliseconds)
beginning_of_song = first_song[:30*1000]

playlist = beginning_of_song
for song in playlist_songs:

    # We don't want an abrupt stop at the end, so let's do a 10 second crossfades
    playlist = playlist.append(song, crossfade=(10 * 1000))

# let's fade out the end of the last song
playlist = playlist.fade_out(30)

# hmm I wonder how long it is... ( len(audio_segment) returns milliseconds )
playlist_length = len(playlist) / (1000*60)

# lets save it!
out_f = open("%s_minute_playlist.mp3" % playlist_length, 'wb')

playlist.export(out_f, format='mp3')
```

## License ([MIT License](http://opensource.org/licenses/mit-license.php))

Copyright © 2011 James Robert, http://jiaaro.com

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

