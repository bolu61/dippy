import logging
import os

import trio

from dippy import spawn_shard

log = logging.getLogger('dippy.shard')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

token = os.environ["DIPPY_TEST_TOKEN"]

async def main():
    async with spawn_shard(token) as shard:
        @shard.hook('send')
        async def _(data):
            print(f'>>># {data}')

        @shard.hook('receive')
        async def _(data):
            print(f'<<<# {data}')


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
