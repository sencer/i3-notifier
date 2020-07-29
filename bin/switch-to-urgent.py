#!/usr/bin/env python3
import asyncio
import logging

import i3ipc
import i3ipc.aio


async def switch():
    async def switch_to_urgent(i3, data):
        i3.main_quit()
        await i3.command(f"workspace {data.current.name}")

    i3 = await i3ipc.aio.Connection(auto_reconnect=True).connect()
    i3.on(i3ipc.Event.WORKSPACE_URGENT, switch_to_urgent)
    await i3.main()


asyncio.run(switch())
