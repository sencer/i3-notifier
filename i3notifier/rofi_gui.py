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
        "30",
        "-markup-rows",
        "-matching",
        "fuzzy",
        "-i",
        "-format",
        "i",
        "-sep",
        r"\x01",
        "--kb-accept-custom",
        "",
        "-kb-custom-1",
        "Ctrl+Delete",
        "-show-icons",
    ]

    def __init__(self, *args, cmd=None):
        self.cmd = cmd or "rofi"
        self._args.extend(args)

    def show_notifications(self, notifications):

        formatted_notifications = [
            notification.formatted() for notification in notifications
        ]

        proc = subprocess.Popen(
            [self.cmd] + self._args, stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )

        proc.stdin.write(self._separator.join(formatted_notifications))
        proc.stdin.close()

        maybe_selection = (lambda x: int(x) if x else None)(
            proc.stdout.read().decode("utf-8")
        )
        operation = Operation(proc.wait())
        return maybe_selection, operation
