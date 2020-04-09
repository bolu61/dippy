from .base import struct

class heartbeat(struct):
    heartbeat_interval: int
    _trace: struct