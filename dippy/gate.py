from .utils.hooks import hook, on
import trio
from trio_websocket import connect_websocket_url
import asks
from contextlib import asynccontextmanager
from json import dumps, loads
from collections import namedtuple
from functools import wraps

import logging
log = logging.getLogger(__name__)

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


@asynccontextmanager
async def open_gate(*args, config = None, **kwargs):
    gateway_url = await get_gateway_url()
    async with trio.open_nursery() as ns:
        yield Gate(ns, await connect_websocket_url(ns, f"{gateway_url}?/v=6&encoding=json", *args, **kwargs)) #TODO parametrizwe the url


async def connect_gate(nursery, *args, config = None, **kwargs):
    gateway_url = get_gateway_url()
    yield Gate(nursery, await connect_websocket_url(nursery, f"{gateway_url}?/v=6&encoding=json", *args, **kwargs))

async def get_gateway_url(config = None):
    r = await asks.get('https://discordapp.com/api/gateway')
    return loads(r.content)['url']


class Gate(trio.abc.Channel):
    def __init__(self, nursery, websocket):
        self._ns = nursery
        self._ws = websocket
        self._hb = None
        self._ls = None
        self._ack = trio.hazmat.ParkingLot()
        self.handlers = {}

        @nursery.start_soon
        async def listener():
            while True:
                r = await self.receive()
                if r.op not in self.handlers:
                    raise #TODO
                self._ns.start_soon(self.handlers[r.op], r.d)

        @on("hello")
        async def heartbeat(hb):
            hb_s = hb / 1000 + 0.5

            while True:
                await self.send(1, self._ls)
                deadline = trio.current_time() + hb_s

                try:
                    with trio.fail_at(deadline):
                        await self._ack.park()
                except trio.TooSlowError:
                    #TODO disconnect and resume
                    raise Exception("too slow lol")
                    return

                await trio.sleep_until(deadline)

        #@hook("hello")
        async def identify(_):
            await self.send(2, {
                'token': '',
                'properties': {
                    '$os': "win10",
                    '$browser': "dippy",
                    '$device': "dippy"
                }
            })

        @self.handler(10)
        @hook("hello")
        async def on_hello(data):
            log.debug("opcode 10 hello received")
            self._hb = data['heartbeat_interval']
            return self._hb

        @self.handler(11)
        async def on_ack(data):
            self._ack.unpark_all()

        @self.handler(0)
        async def on_dispatch(data):
            print(data)

    def handler(self, opcode):
        def decorate(f):
            self.handlers[opcode] = f
            return f
        return decorate

    async def aclose(self):
        return await self._ws.aclose()

    async def send(self, *args):
        @hook("send")
        async def _send():
            r = Payload(*args)
            await self._ws.send_message(str(r))
            return r
        await _send()

    @hook("receive")
    async def receive(self):
        return Payload.from_str(await self._ws.get_message())

