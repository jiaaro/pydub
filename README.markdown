# Installation

copy the pydub director into your python path 

-OR-

  pip install pydub


# Dependencies

requires lame for mp3 encoding and decoding

 - lame (http://lame.sourceforge.net/)


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
