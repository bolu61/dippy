from hookt import trigger, hook, HooksMixin, TriggerGroup
from .payload import Payload

import trio
from trio_websocket import connect_websocket_url
import asks
from contextlib import asynccontextmanager
from json import dumps, loads
from collections import namedtuple
from functools import partial
import logging

log = logging.getLogger(__name__)


@asynccontextmanager
async def create_shard(*args, **kwargs):
    gateway_url = await get_gateway_url()
    async with trio.open_nursery() as ns:
        async with Shard(ns, await connect_websocket_url(ns, f"{gateway_url}?/v=6&encoding=json", *args, **kwargs)) as s:
            yield s



async def get_gateway_url(config = None):
    r = await asks.get('https://discordapp.com/api/gateway')
    return loads(r.content)['url']



class Shard(trio.abc.Channel, HooksMixin):

    hooks = TriggerGroup()

    def __init__(self, nursery, websocket):
        self.ns = nursery
        self.ws = websocket
        self.hb = None
        self.ls = None
        self.ack_lot = trio.hazmat.ParkingLot()
        self.handlers = {}

        @nursery.start_soon
        @self.hooks.trigger("stop")
        async def listener():
            while True:
                r = await self.receive()
                if r.op not in self.handlers:
                    raise #TODO
                nursery.start_soon(self.handlers[r.op], r.d)

        async def identify(self, _):
            await self.send(2, {
                'token': '',
                'properties': {
                    '$os': "win10",
                    '$browser': "dippy",
                    '$device': "dippy"
                }
            })

        @self.set_handler(0)
        @self.hooks.trigger("dispatch")
        async def on_dispatch(data):
            log.debug(data)
            return data

        @self.set_handler(10)
        @self.hooks.trigger("hello")
        async def on_hello(data):
            log.debug("opcode 10 hello received")
            self.hb = data['heartbeat_interval']
            return self.hb

        @self.set_handler(11)
        @self.hooks.trigger("heartbeat")
        async def on_ack(data):
            self.ack_lot.unpark_all()


        @self.hooks.hook("hello")
        @self.hooks.trigger("hearbeat_stop")
        async def heartbeat(hb):
            hb_s = hb / 1000 + 0.5

            while True:
                await self.send(1, self.ls)
                deadline = trio.current_time() + hb_s

                try:
                    with trio.fail_at(deadline):
                        await self.ack_lot.park()
                except trio.TooSlowError:
                    #TODO disconnect and resume
                    raise Exception("too slow lol")

                await trio.sleep_until(deadline)


    def set_handler(self, opcode):
        def decorate(f):
            self.handlers[opcode] = f
            return f
        return decorate

    @hooks.trigger("close")
    async def aclose(self):
        await trio.checkpoint()
        print("hello")
        return await self.ws.aclose()


    @hooks.trigger("send")
    async def send(self, *args):
        r = Payload(*args)
        await self.ws.send_message(str(r))
        return r


    @hooks.trigger("receive")
    async def receive(self):
        return Payload.from_str(await self.ws.get_message())

