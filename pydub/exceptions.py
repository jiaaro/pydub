class PydubException(Exception):
    """
    Base class for any Pydub exception
    """


class TooManyMissingFrames(PydubException):
    pass


class InvalidDuration(PydubException):
    pass


class InvalidTag(PydubException):
    pass


class InvalidID3TagVersion(PydubException):
    pass


class CouldntDecodeError(PydubException):
    pass


class CouldntEncodeError(PydubException):
    pass


class MissingAudioParameter(PydubException):
    pass


class ConverterNotFoundError(PydubException, FileNotFoundError):
    """
    ffmpeg/avconv (or ffprobe/ffplay) could not be run. Subclasses
    FileNotFoundError/OSError so existing ``except OSError`` handlers keep
    working.
    """
