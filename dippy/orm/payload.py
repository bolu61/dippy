from reprlib import repr

from .base import struct

class payload(struct):
    op: int
    d: struct
    s: int
    t: str

    def __repr__(self):
        if self.op == 0:
            return f"<{type(self).__name__}/00#{self.s} {self.t} {repr(self.d.data)}>"
        else:
            return f"<{type(self).__name__}/{self.op:02} {repr(self.d.data)}>"
