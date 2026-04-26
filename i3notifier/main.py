import argparse
import logging
import logging.handlers
import os
import signal
import sys

import daemon
import daemon.pidfile
import dbus
import dbus.mainloop.glib
from gi.repository import GLib

from i3notifier.data_manager import DataManager
from i3notifier.notification_fetcher import NotificationFetcher
from i3notifier.rofi_gui import RofiGUI
from i3notifier.user_config import get_user_config

logger = logging.getLogger("i3notifier")
files_preserve = []


def run_daemon(config_path=None, nodaemon=False):
  try:
    userconfig = get_user_config(config_path)
  except FileNotFoundError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

  logger.info(f"Found {len(userconfig.config_list)} configurations.")

  state_home = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
  dump_path = os.path.join(state_home, "i3-notifier", "dump")
  os.makedirs(os.path.dirname(dump_path), exist_ok=True)

  logger.info(
    f"Notifications will be dumped to {dump_path} on graceful exit or when asked."
  )
  data_manager = DataManager(userconfig.config_list, dump_path)

  gui = RofiGUI(theme=userconfig.theme)

  def dump_and_exit(n, f):
    data_manager.dump()
    data_manager.cancel_timers()
    sys.exit(0)

  runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
  pid_file = os.path.join(runtime_dir, "i3-notifier.pid")

  if os.path.exists(pid_file):
    try:
      pid = int(open(pid_file).read().strip())
      os.kill(pid, 0)
      logger.info(f"i3-notifier is already running with pid {pid}.")
    except (ProcessLookupError, ValueError):
      os.remove(pid_file)
      logger.info("i3-notifier is not running, but a lock file exists. Cleaning up.")

  def run():
    logger.info(f"Creating lock file {pid_file}")
    with open(pid_file, "w") as f:
      f.write(str(os.getpid()))

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    NotificationFetcher(data_manager, gui)

    logger.info("Starting i3-notifier.")
    try:
      GLib.MainLoop().run()
    except (Exception, KeyboardInterrupt) as e:
      logger.info(f"Exiting Glib.MainLoop: {e}")
      data_manager.dump()
    finally:
      if os.path.exists(pid_file):
        os.remove(pid_file)

  if nodaemon:
    run()
  else:
    with daemon.DaemonContext(
      pidfile=daemon.pidfile.PIDLockFile(pid_file),
      signal_map={signal.SIGTERM: dump_and_exit},
      files_preserve=files_preserve,
    ):
      run()


def main():
  parser = argparse.ArgumentParser(description="i3-notifier daemon")
  parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging. Logs will be written to /tmp/i3-notifier.log.",
  )
  parser.add_argument(
    "--config",
    "-c",
    help=(
      "Path to custom user configuration file. "
      "Defaults to $XDG_CONFIG_HOME/i3/i3_notifier_config.py "
      "or ~/.config/i3/i3_notifier_config.py if not specified."
    ),
  )
  parser.add_argument(
    "--nodaemon",
    action="store_true",
    help="Run in the foreground instead of as a daemon.",
  )
  parser.add_argument(
    "--dump",
    action="store_true",
    help="Command the running daemon to dump notifications to file and exit.",
  )
  parser.add_argument(
    "--kill",
    action="store_true",
    help="Kill the running daemon instance and exit.",
  )
  args = parser.parse_args()

  if args.dump:
    bus = dbus.SessionBus()
    try:
      obj = bus.get_object(
        "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
      )
      obj.DumpNotifications(dbus_interface="org.freedesktop.Notifications")
      print("Notifications dumped to /tmp/i3-notifier.dump")
      sys.exit(0)
    except dbus.exceptions.DBusException as e:
      print(f"Error communicating with daemon: {e}", file=sys.stderr)
      sys.exit(1)

  if args.kill:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    pid_file = os.path.join(runtime_dir, "i3-notifier.pid")
    if os.path.exists(pid_file):
      try:
        with open(pid_file) as f:
          pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to process {pid}")
        sys.exit(0)
      except ProcessLookupError:
        print(f"Process {pid} not found. Cleaning up pid file.")
        os.remove(pid_file)
        sys.exit(0)
      except Exception as e:
        print(f"Error killing process: {e}", file=sys.stderr)
        sys.exit(1)
    else:
      print("i3-notifier is not running (pid file not found).")
      sys.exit(0)

  global files_preserve

  if args.debug:
    if args.nodaemon:
      handler = logging.StreamHandler(sys.stderr)
    else:
      state_home = os.environ.get(
        "XDG_STATE_HOME", os.path.expanduser("~/.local/state")
      )
      log_path = os.path.join(state_home, "i3-notifier", "log")
      os.makedirs(os.path.dirname(log_path), exist_ok=True)
      handler = logging.FileHandler(log_path, "w")
      files_preserve.append(handler.stream.fileno())

    handler.setFormatter(
      logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

  run_daemon(config_path=args.config, nodaemon=args.nodaemon)


if __name__ == "__main__":
  main()
