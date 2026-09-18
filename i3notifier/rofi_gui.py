import logging
import os.path
import subprocess
import sys
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
  use_script_mode = True
  __slots__ = "cmd", "_args", "_theme_args", "_proc"

  def __init__(self, *args, theme=None, cmd=None):
    self.cmd = cmd or "rofi"
    self._theme_args = []
    if theme is not None:
      theme_file = theme if theme.endswith(".rasi") else f"{theme}.rasi"
      built_in_theme = os.path.join(os.path.dirname(__file__), "rofi-theme", theme_file)
      if os.path.exists(built_in_theme):
        self._theme_args = ["-theme", built_in_theme]
      elif os.path.exists(theme):
        self._theme_args = ["-theme", theme]
      else:
        self._theme_args = ["-theme", built_in_theme]

    self._args = [
      "-dmenu",
      "-markup-rows",
      "-i",
      "-format",
      "i",
      "-sep",
      r"\x01",
    ] + list(args) + self._theme_args
    self._proc = None

  def is_running(self):
    return self._proc is not None and self._proc.poll() is None

  def close(self):
    if self.is_running():
      try:
        self._proc.terminate()
      except (ProcessLookupError, OSError):
        pass
    self._proc = None

  def launch_script_mode(self, exit_callback=None):
    if self.is_running():
      self.close()
      return None

    agent_cmd = f"{sys.executable} -m i3notifier.rofi_agent"
    cmd = [
      self.cmd,
      "-show",
      "i3notifier",
      "-modes",
      f"i3notifier:{agent_cmd}",
      *self._theme_args,
    ]
    self._proc = subprocess.Popen(cmd)
    if exit_callback:
      try:
        from gi.repository import GLib

        GLib.child_watch_add(self._proc.pid, exit_callback)
      except Exception as e:
        logger.warning(f"Could not register child_watch_add: {e}")
    return self._proc

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

    stdout_data, _ = proc.communicate(
      input=self._separator.join(formatted_notifications)
    )
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
