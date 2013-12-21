import subprocess
from tempfile import NamedTemporaryFile
from .utils import get_player_name

PLAYER = get_player_name()

def play(audio_segment):
    with NamedTemporaryFile("w+b", suffix=".wav") as f:
        audio_segment.export(f.name, "wav")
        subprocess.call([PLAYER, "-nodisp", "-autoexit", f.name])
