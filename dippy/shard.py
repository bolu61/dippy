"""shard
"""

from contextlib import asynccontextmanager
from json import dumps, loads
from typing import Tuple, Mapping, Callable, Any

import logging

from trio import Nursery
from hookt import HooksMixin, TriggerGroup
from trio_websocket import connect_websocket_url, WebSocketConnection

import trio
import asks

from .orm import payload, heartbeat

log = logging.getLogger(__name__)


@asynccontextmanager
async def spawn_shard(token, shard_id=None):
    """TODO"""
    if shard_id is None:
        shard_id = [0, 1]
    url = await _get_gateway_url(token)
    async with trio.open_nursery() as ns:
        ws = await connect_websocket_url(ns, url)
        async with Shard(ns, ws, token, shard_id) as shard:
            yield shard
            await shard.run()
        await ws.aclose()


async def _get_gateway_url(token, endpoint='https://discordapp.com/api/gateway/bot'):
    r = await asks.get(endpoint, headers={'Authorization': f'Bot {token}'})
    return loads(r.content)['url']






class Shard(trio.abc.Channel, HooksMixin):

    hooks = TriggerGroup()

    def __init__(self, nursery: Nursery, websocket: WebSocketConnection, token: str, shard_id: Tuple[int,int] = (0,1), buffer_size: int = 32):
        self.heartbeat = None
        self.heartbeat_scope = None

        self.ns = nursery
        self.ws = websocket
        self.hb = None
        self.ls = None

        self.handlers = {}
        self.token = token
        self.shard_id = shard_id
        self.heartbeat = None

        self.dptch_queue, self.event_queue = trio.open_memory_channel(buffer_size)

        self.handlers[0] = self.on_dispatch
        self.handlers[10] = self.on_hello
        self.handlers[11] = self.on_heartbeat


    @hooks.trigger("stop")
    async def run(self):
        """TODO"""
        log.debug("%s starting", self)
        self.heartbeat = trio.hazmat.ParkingLot()
        async for r in self:
            if r.op not in self.handlers:
                raise NotImplementedError(f"handler for {r.op}") #TODO
            self.ns.start_soon(self.handlers[r.op], r)
        log.debug(f"{self}'s main loop stopped")


    @hooks.trigger("dispatch")
    async def on_dispatch(self, payload):
        self.ls = payload.s
        return payload.t, payload.d, payload.s


    @hooks.trigger("hello")
    async def on_hello(self, payload):
        self.hb = payload.d.heartbeat_interval

        self.ns.start_soon(self.heartbeating)

        r = {
            'token': self.token,
            'properties': {
                '$os': "win10",
                '$browser': "dippy",
                '$device': "dippy"
            },
            'shard': self.shard_id
        }

        await self.send(2, r)

        return r


    @hooks.trigger("heartbeat")
    async def on_heartbeat(self, payload):
        if not self.heartbeat:
            raise RuntimeError(f"{self} is closed, but still received a heartbeat") # TODO: define custom exception

        self.heartbeat.unpark_all()
        return heartbeat(payload.d)


    async def heartbeating(self):
        hb_s = self.hb / 1000 + 0.5
        if self.heartbeat is None:
            raise RuntimeError(f"{self} is closed, cannot start heartbeat")

        log.debug(f"{self} started")
        while self.heartbeat is not None:
            await self.send(1, self.ls)
            deadline = trio.current_time() + hb_s
            with trio.move_on_at(deadline) as heartbeat_scope:
                heartbeat_scope.shield = True
                self.heartbeat_scope = heartbeat_scope
                await self.heartbeat.park()
            if heartbeat_scope.cancel_called:
                #TODO disconnect or resume or
                log.debug(f"{self}'s heartbeat stopped")
            await trio.sleep_until(deadline)



    @hooks.trigger("close")
    async def aclose(self):
        if self.heartbeat is not None:
            log.debug(f"{self} closing")
            if self.heartbeat_scope is not None:
                self.heartbeat_scope.cancel()
            await self.dptch_queue.aclose()
            await self.event_queue.aclose()

        log.debug(f"{self} closed")
        return


    @hooks.trigger("send")
    async def send(self, op, d, s=None, t=None):
        r = payload(op=op, d=d, s=s, t=t)
        await self.ws.send_message(dumps(r.data))
        return r


    @hooks.trigger("receive")
    async def receive(self):
        return payload(loads(await self.ws.get_message()))

