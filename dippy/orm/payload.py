from typing import Optional

from .orm import packet

class payload(packet):
    op: int
    d: packet
    s: Optional[int]
    t: Optional[str]