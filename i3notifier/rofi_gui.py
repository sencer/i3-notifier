import os.path
import subprocess
from enum import Enum


class Operation(Enum):
    SELECT = 0
    EXIT = 1
    DELETE = 10


class RofiGUI:

    _separator = b"\x01"
    _args = [
        "-dmenu",
        "-markup-rows",
        "-i",
        "-format",
        "i",
        "-sep",
        r"\x01",
    ]

    __slots__ = "cmd"

    def __init__(self, *args, theme=None, cmd=None):
        self.cmd = cmd or "rofi"
        self._args.extend(args)
        if theme is not None:
            self._args.extend(
                ["-theme", f"{os.path.dirname(__file__)}/rofi-theme/{theme}"]
            )

    def show_notifications(self, notifications, row=0):

        formatted_notifications = []
        urgent = []
        active = []
        for i, notification in enumerate(notifications):
            formatted_notifications.append(notification.formatted())

            if notification.urgency == 2:
                urgent.append(str(i))

            if len(notification) > 1:
                active.append(str(i))

        proc = subprocess.Popen(
            [self.cmd]
            + self._args
            + ["-selected-row", str(row)]
            + (["-u", ",".join(urgent)] if urgent else [])
            + (["-a", ",".join(active)] if active else []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        proc.stdin.write(self._separator.join(formatted_notifications))
        proc.stdin.close()

        maybe_selection = (lambda x: int(x) if x else None)(
            proc.stdout.read().decode("utf-8")
        )
        operation = Operation(proc.wait())
        return maybe_selection, operation
