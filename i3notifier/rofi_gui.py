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
        "-p",
        "Notifications",
        "-eh",
        "2",
        "-width",
        "-40",
        "-markup-rows",
        "-i",
        "-format",
        "i",
        "-sep",
        r"\x01",
        "--kb-accept-custom",
        "",
        "--kb-accept-alt",
        "",
        "-kb-custom-1",
        "Ctrl+Delete",
        "-show-icons",
        "-columns",
        "1",
        "-lines",
        "10",
    ]

    __slots__ = 'cmd'

    def __init__(self, *args, cmd=None):
        self.cmd = cmd or "rofi"
        self._args.extend(args)

    def show_notifications(self, notifications, row=0):

        formatted_notifications = [
            notification.formatted() for notification in notifications
        ]

        urgent = [
            str(i)
            for i, notification in enumerate(notifications)
            if notification.urgency == 2
        ]

        proc = subprocess.Popen(
            [self.cmd]
            + self._args
            + ["-selected-row", str(row)]
            + (["-u", ",".join(urgent)] if urgent else []),
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
