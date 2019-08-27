from .configuration import make
from .ice import freeze
from .gate import open_gate

import trio
from trio.abc import Channel
import asks
import json
from functools import partial
from urllib.parse import urlencode

__all__ = ["Bot"]

class Bot(Channel):
    """"""
    def __init__(self):
        self.session = None
        self.gate = None

    async def aclose():
        pass #TODO

    async def send():
        pass #TODO

    async def receive(self):
        pass #TODO

    @property
    def conf(self):
        """"""
        return self._conf