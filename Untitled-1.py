import dippy.gate as gate
from dippy.utils.hooks import on

import trio
@trio.run
async def main():
    async with gate.open_gate() as g:
        @on("send")
        async def _(data):
            print(f">>>{data}")
        @on("receive")
        async def _(data):
            print(f"<<<{data}")

