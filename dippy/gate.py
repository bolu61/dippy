import trio
from trio.abc import AsyncResource
from trio_websocket import open_websocket_url
from contextlib import asynccontextmanager
from json import dumps, loads
from collections import namedtuple

class Payload(namedtuple("_Payload", "op d s t")):
    @classmethod
    def from_str(data):
        d = json.loads(data)
        Payload(**d)
    def __str__(self):
        return json.dumps(self._asdict())
    def __getitem__(self, key):
        if isinstance(key, str):
            return getattr(self, key)
        else:
            return super().__getitem__(key)

@asynccontextmanager
async def open_gate(*args, **kwargs):
    with open_websocket_url(*args, **kwargs) as ws:
        yield Gate(ws)


class Gate(AsyncResource):
    def __init__(self, ws):
        self._ws = ws

    async def aclose(self):
        self._ws.aclose()

    async def send(self, op, d, s, t):
        self._ws.send_message(str(Payload(op, d, s, t)))

    async def recv(self):
        Payload.from_str(self._ws.get_message())
