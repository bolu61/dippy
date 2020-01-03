from dippy.shard import spawn_shard
from dippy.utils.hooks import hook

import trio
@trio.run
async def main():
    async with spawn_shard() as g:
        @hook(g.send)
        async def _(data):
            print(f">>>{data}")
        @hook(g.receive)
        async def _(data):
            print(f"<<<{data}")
