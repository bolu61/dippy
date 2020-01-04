from dippy.shard import spawn_shard

import trio

@trio.run
async def main():

    async with spawn_shard() as g:

        @g.hook('send')
        async def _(data):
            print(f">>>{data}")

        @g.hook('receive')
        async def _(data):
            print(f"<<<{data}")
