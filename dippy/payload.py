from json import loads, dumps
from collections import namedtuple

class Payload(namedtuple("_Payload", ("op", "d", "s", "t"), defaults = (None, None, None, None))):
    @classmethod
    def from_str(cls, data):
        d = loads(data)
        return Payload(**d)
    def __str__(self):
        return dumps(self._asdict())
    def __getitem__(self, key):
        if isinstance(key, str):
            return getattr(self, key)
        else:
            return super().__getitem__(key)