

class TooManyMissingFrames(Exception):
    pass


class InvalidDuration(Exception):
    pass


class InvalidTag(Exception):
    pass


class InvalidID3TagVersion(Exception):
    pass


class CouldntDecodeError(Exception):
    pass
    
class CouldntEncodeError(Exception):
    pass

class MissingAudioParameter(Exception):
    pass