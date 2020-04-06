from dippy.shard import spawn_shard

import trio
import logging

log = logging.getLogger('dippy.shard')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

async def main():
    async with spawn_shard('Njk1MzQwMjg4MjUxNTI3MjM4.XoaYxg.YgYARGxwG8oV5sxUIkg7cu2ZzxM') as shard:
        @shard.hook('send')
        async def _(data):
            print(f'>>>{data}')

        @shard.hook('receive')
        async def _(data):
            print(f'<<<{data}')


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
