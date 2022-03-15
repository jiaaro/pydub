import os
try:
    _ = os.environ['PYDUB_NO_WINDOW']
except KeyError:
    os.environ["PYDUB_NO_WINDOW"] = "0"

from .audio_segment import AudioSegment
