# Pydub [![Build Status](https://secure.travis-ci.org/jiaaro/pydub.png?branch=master)](http://travis-ci.org/jiaaro/pydub)
Pydub let's you do stuff to audio in a way that isn't stupid.

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

first_10_seconds = song[:10000]

last_5_seconds = song[5000:]
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

You can pass an optional bitrate argument to export using any syntax ffmpeg supports.

```python
awesome.export("mashup.mp3", format="mp3", bitrate="192k")
```    

Any further arguments supported by ffmpeg can be passed as a list in a 'parameters' argument, with switch first, argument second. Note that no validation takes place on these parameters, and you may be limited by what your particular build of ffmpeg supports.

```python
# Use preset mp3 quality 0 (equivalent to lame V0)
awesome.export("mashup.mp3", format="mp3", parameters=["-q:a", "0"])

# Mix down to two channels and set hard output volume
awesome.export("mashup.mp3", format="mp3", parameters=["-ac", "2", "-vol", "150"])
```    

## Installation

Copy the pydub directory into your python path. Zip [here](https://github.com/jiaaro/pydub/zipball/master)

-OR-

    pip install pydub

-OR-

    git clone https://github.com/jiaaro/pydub.git

## Dependencies

Requires ffmpeg or avconv for encoding and decoding all non-wav files (which work natively)

 - ffmpeg (http://www.ffmpeg.org/)
 
 -OR-

 - avconv (http://libav.org/)

## Important Notes

`AudioSegment` objects are [immutable](http://www.devshed.com/c/a/Python/String-and-List-Python-Object-Types/1/)

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
    playlist.append(song, crossfade=(10 * 1000))

# let's fade out the end of the last song
playlist = playlist.fade_out(30)

# hmm I wonder how long it is... ( len(audio_segment) returns milliseconds )
playlist_length = len(playlist) / (1000*60)

# lets save it!
out_f = open("%s_minute_playlist.mp3" % playlist_length, 'wb')

playlist.export(out_f, format='mp3')
```

### Yet another Example?

Let's say you have a weekly podcast and you want to do the processing automatically.

For this example we're going to:
 
  - Strip out the silence
  - Add on the bumpers (intro/outro theme music)

```python
from pydub import AudioSegment
from pydub.utils import db_to_float

# Let's load up the audio we need...
podcast = AudioSegment.from_mp3("podcast.mp3")
intro = AudioSegment.from_wav("intro.wav")
outro = AudioSegment.from_wav("outro.wav")

# Let's consider anything that is 30 decibels quieter than
# the average volume of the podcast to be silence
average_loudness = podcast.rms
silence_threshold = average_loudness * db_to_float(-30)

# filter out the silence
podcast_parts = (ms for ms in podcast if ms.rms > silence_threshold)

# combine all the chunks back together
podcast = reduce(lambda a, b: a + b, podcast_parts)

# add on the bumpers
podcast = intro + podcast + outro

# save the result
podcast.export("podcast_processed.mp3", format="mp3")
```




    
Not bad!

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

