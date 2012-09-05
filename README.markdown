[![Build Status](https://secure.travis-ci.org/jiaaro/pydub.png?branch=master)](http://travis-ci.org/jiaaro/pydub)

# Overview

Pydub let's you do stuff to audio in a way that isn't stupid.

Open a WAV file

    from pydub import AudioSegment
    
    song = AudioSegment.from_wav("never_gonna_give_you_up.wav")
    
...or an mp3

    song = AudioSegment.from_mp3("never_gonna_give_you_up.mp3")
    
... or an ogg, or flv, or [anything else ffmpeg supports](http://www.iepak.com/35/TopicDetail.aspx)
    
    ogg_version = AudioSegment.from_ogg("never_gonna_give_you_up.ogg")
    flv_version = AudioSegment.from_flv("never_gonna_give_you_up.flv")
    
    mp4_version = AudioSegment.from_file("never_gonna_give_you_up.mp4", "mp4")
    wma_version = AudioSegment.from_file("never_gonna_give_you_up.wma", "wma")
    aac_version = AudioSegment.from_file("never_gonna_give_you_up.aiff", "aac")
    
Slice audio
    
    # pydub does things in miliseconds
    ten_seconds = 10 * 1000
    
    first_10_seconds = song[:10000]
    
    last_5_seconds = song[5000:]
    
Make the beginning louder and the end quieter
    
    # boost volume by 6dB
    beginning = first_10_seconds + 6
    
    # reduce volume by 3dB
    end = last_5_seconds - 3
    
Concatenate audio (add one file to the end of another)
    
    without_the_middle = beginning + end
    
AudioSegments are immutable
    
    # song is not modified
    backwards = song.reverse()
    
Crossfade (again, beginning and end are not modified)
    
    # 1.5 second crossfade
    with_style = beginning.append(end, crossfade=1500)
    
Repeat

    # repeat the clip twice
    do_it_over = with_style * 2
    
Fade (note that you can chain operations because everything returns
an AudioSegment)
    
    # 2 sec fade in, 3 sec fade out
    awesome = do_it_over.fade_in(2000).fade_out(3000)
    
Save the results (again whatever ffmpeg supports)

    awesome.export("mashup.mp3", format="mp3")
    

# Installation

copy the pydub director into your python path 

-OR-

  pip install pydub


# Dependencies

requires ffmpeg for encoding and decoding all non-wav files (which work natively)

 - ffmpeg (http://www.ffmpeg.org/)

# Example Use

	from pydub import AudioSegment

	song = AudioSegment.from_mp3(song_mp3_file)
	dj_intro = AudioSegment.from_mp3(some_mp3_of_a_dj)
	
	# let's just include the first 30 seconds of the song in the
	# promotional clip (slicing is done by milliseconds)
	beginning_of_song = song[:30*1000]

	# We don't want an abrupt stop at the end, so let's do a 5 second fadeout
	beginning_of_song = beginning_of_song.fade_out(5 * 1000)

	# 50 ms crossfade to eliminate pops
	promo_clip = dj_intro.append(beginning_of_song, crossfade=50)
	
	# hmm I wonder how long it is... ( len(audio_segment) returns milliseconds )
	promo_length = len(promo_clip) / 1000
	
	# lets save it!
	out_f = open("%s_second_promo_clip.mp3" % promo_length, 'wb')
	shout.export(out_f, format='mp3')
