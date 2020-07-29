#!/usr/bin/env python3
import logging

import i3ipc


def switch():
    def switch_to_urgent(i3, data):
        i3.main_quit()
        i3.command(f"workspace {data.current.name}")

    i3 = i3ipc.Connection(auto_reconnect=True)
    i3.on(i3ipc.Event.WORKSPACE_URGENT, switch_to_urgent)
    i3.main(3)


switch()
