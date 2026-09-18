import logging
import os.path
import subprocess
from enum import Enum

logger = logging.getLogger(__name__)


class Operation(Enum):
  SELECT = 0
  EXIT_COMPLETELY = 1
  DELETE = 10
  EXIT = 11
  SELECT_ALT = 12
  DELETE_ALT = 13


class RofiGUI:
  _separator = b"\x01"
  __slots__ = "cmd", "_args"

  def __init__(self, *args, theme=None, cmd=None):
    self.cmd = cmd or "rofi"
    self._args = [
      "-dmenu",
      "-markup-rows",
      "-i",
      "-format",
      "i",
      "-sep",
      r"\x01",
    ] + list(args)
    if theme is not None:
      theme_file = theme if theme.endswith(".rasi") else f"{theme}.rasi"
      built_in_theme = os.path.join(os.path.dirname(__file__), "rofi-theme", theme_file)
      if os.path.exists(built_in_theme):
        self._args.extend(["-theme", built_in_theme])
      elif os.path.exists(theme):
        self._args.extend(["-theme", theme])
      else:
        self._args.extend(["-theme", built_in_theme])

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

    stdout_data, _ = proc.communicate(input=self._separator.join(formatted_notifications))
    raw_selection = stdout_data.decode("utf-8").strip() if stdout_data else ""
    try:
      maybe_selection = int(raw_selection) if raw_selection else None
    except ValueError:
      maybe_selection = None

    operation = proc.returncode
    logger.info(f"Operation {operation}")
    try:
      op = Operation(operation)
    except ValueError:
      op = Operation.EXIT_COMPLETELY

    return maybe_selection, op
