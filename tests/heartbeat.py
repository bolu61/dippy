from dippy.shard import create_shard

import trio

@trio.run
async def main():
    async with create_shard() as g:
        print(g)
        @g.hook('send')
        async def _(data):
            print(f">>>{data}")

        @g.hook('receive')
        async def _(data):
            print(f"<<<{data}")
