import io
import json
import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from i3notifier.config import Config
from i3notifier.data_manager import DataManager
from i3notifier.notification import Notification, NotificationCluster
from i3notifier.notification_fetcher import NotificationFetcher
from i3notifier.rofi_ipc import RofiIPCServer, get_socket_path


class DummyConfig(Config):
  def get_keys(notification):
    return (notification.app_name, notification.summary)


class TestRofiIPC(unittest.TestCase):
  def setUp(self):
    self.temp_dir = tempfile.TemporaryDirectory()
    self.socket_path = os.path.join(self.temp_dir.name, "test_rofi.sock")

  def tearDown(self):
    self.temp_dir.cleanup()

  def test_ipc_server_request_response(self):
    def echo_handler(req):
      return {"action": "render", "echo": req.get("test")}

    server = RofiIPCServer(echo_handler, socket_path=self.socket_path)
    try:
      import socket
      client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      client.connect(self.socket_path)
      client.sendall(json.dumps({"test": "hello"}).encode("utf-8") + b"\n")
      # Let GLib / socket process
      # Since we're in a unit test without GLib.MainLoop running, invoke _on_connection directly
      server._on_connection(server.sock.fileno(), None)
      resp_data = client.recv(4096)
      client.close()
      resp = json.loads(resp_data.decode("utf-8"))
      self.assertEqual(resp.get("action"), "render")
      self.assertEqual(resp.get("echo"), "hello")
    finally:
      server.close()


class TestRofiAgent(unittest.TestCase):
  def test_rofi_agent_renders_output(self):
    from i3notifier import rofi_agent

    resp_json = (
      json.dumps({
        "action": "render",
        "prompt": "CustomPrompt",
        "keep_selection": True,
        "urgent": [0],
        "active": [1],
        "entries": ["Item1\0icon\x1fi1\x1finfo\x1f1", "Item2\0icon\x1fi2\x1finfo\x1f2"],
      }).encode("utf-8")
      + b"\n"
    )

    with patch("socket.socket") as mock_socket_cls:
      mock_sock = MagicMock()
      mock_socket_cls.return_value = mock_sock
      mock_sock.recv.side_effect = [resp_json, b""]

      stdout_capture = io.StringIO()
      with patch("sys.stdout", stdout_capture):
        with patch.dict(os.environ, {"ROFI_RETV": "0", "ROFI_INFO": ""}):
          rofi_agent.main()

      output = stdout_capture.getvalue()
      self.assertIn("\x00use-hot-keys\x1ftrue\n", output)
      self.assertIn("\x00markup-rows\x1ftrue\n", output)
      self.assertIn("\x00no-custom\x1ftrue\n", output)
      self.assertIn("\x00delim\x1f\x01\n", output)
      self.assertIn("\x00keep-selection\x1ftrue\n", output)
      self.assertIn("\x00prompt\x1fCustomPrompt\n", output)
      self.assertIn("\x00urgent\x1f0\n", output)
      self.assertIn("\x00active\x1f1\n", output)
      self.assertIn(
        "Item1\x00icon\x1fi1\x1finfo\x1f1\x01Item2\x00icon\x1fi2\x1finfo\x1f2\x01",
        output,
      )

  def test_rofi_agent_action_close_exits_cleanly(self):
    from i3notifier import rofi_agent

    resp_json = json.dumps({"action": "close"}).encode("utf-8") + b"\n"

    with patch("socket.socket") as mock_socket_cls:
      mock_sock = MagicMock()
      mock_socket_cls.return_value = mock_sock
      mock_sock.recv.side_effect = [resp_json, b""]

      stdout_capture = io.StringIO()
      with patch("sys.stdout", stdout_capture):
        with patch.dict(os.environ, {"ROFI_RETV": "1", "ROFI_INFO": "leaf:1"}):
          with self.assertRaises(SystemExit) as cm:
            rofi_agent.main()
          self.assertEqual(cm.exception.code, 0)

      self.assertEqual(stdout_capture.getvalue(), "")

  def test_rofi_agent_socket_unavailable_exits_cleanly(self):
    from i3notifier import rofi_agent

    with patch("socket.socket") as mock_socket_cls:
      mock_sock = MagicMock()
      mock_socket_cls.return_value = mock_sock
      mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")

      stdout_capture = io.StringIO()
      with patch("sys.stdout", stdout_capture):
        with self.assertRaises(SystemExit) as cm:
          rofi_agent.main()
        self.assertEqual(cm.exception.code, 0)
      self.assertEqual(stdout_capture.getvalue(), "")



class TestRofiScriptStateMachine(unittest.TestCase):
  def setUp(self):
    self.gio_patcher = patch("i3notifier.notification_fetcher.Gio")
    self.mock_gio = self.gio_patcher.start()

    self.dm = DataManager([DummyConfig], "/dev/null")
    now = time.time_ns()
    # Add two notifications in cluster ("A1", "1")
    self.n1 = Notification(1, "A1", "icon1", "1", "body1", ["dflt"], now, urgency=1)
    self.n2 = Notification(2, "A1", "icon2", "1", "body2", ["dflt"], now + 1, urgency=1)
    # Add one notification in cluster ("A2", "2") with urgency 2
    self.n3 = Notification(3, "A2", "icon3", "2", "body3", ["dflt"], now + 2, urgency=2)
    self.dm.add_notification(self.n1)
    self.dm.add_notification(self.n2)
    self.dm.add_notification(self.n3)

    self.gui = MagicMock()
    self.gui.use_script_mode = True
    self.fetcher = NotificationFetcher(self.dm, self.gui, start_ipc=False)
    self.fetcher.ActionInvoked = MagicMock()
    self.fetcher.NotificationClosed = MagicMock()

  def tearDown(self):
    self.fetcher.close()
    self.gio_patcher.stop()

  def test_retv_0_initial_render(self):
    resp = self.fetcher.handle_rofi_request({"retv": 0})
    self.assertEqual(resp["action"], "render")
    self.assertEqual(resp["prompt"], "Notifications")
    self.assertFalse(resp["keep_selection"])
    # 2 top-level clusters: A1 (2 items) and A2 (1 item)
    self.assertEqual(len(resp["entries"]), 2)
    # A2 has urgency 2, so index 0 is urgent (sorted by urgency desc)
    self.assertIn(0, resp["urgent"])
    # A1 has 2 items, so it is active (group)
    self.assertIn(1, resp["active"])

  def test_retv_1_drill_down_and_leaf_action(self):
    # Drill down into A1
    resp = self.fetcher.handle_rofi_request({"retv": 1, "info": "cluster:A1"})
    self.assertEqual(resp["action"], "render")
    self.assertEqual(self.fetcher.rofi_context, ["A1"])

    # Now inside A1, select leaf 2 (enter)
    resp2 = self.fetcher.handle_rofi_request({"retv": 1, "info": "leaf:2"})
    # Leaf selection invokes action and closes Rofi to release Wayland grab
    self.assertEqual(resp2["action"], "close")
    self.fetcher.ActionInvoked.assert_called_once_with(2, "default")
    self.fetcher.NotificationClosed.assert_called_once_with(2, 2)
    self.assertNotIn(2, self.dm.map)

  def test_retv_10_delete_notification(self):
    resp = self.fetcher.handle_rofi_request({"retv": 10, "info": "leaf:3"})
    self.assertEqual(resp["action"], "render")
    self.assertTrue(resp["keep_selection"])
    self.fetcher.NotificationClosed.assert_called_once_with(3, 2)
    self.assertNotIn(3, self.dm.map)

  def test_retv_10_delete_last_notification_closes(self):
    self.dm.remove_notification(1)
    self.dm.remove_notification(2)
    # Only notification 3 remains
    resp = self.fetcher.handle_rofi_request({"retv": 10, "info": "leaf:3"})
    # With all notifications removed, Rofi should close
    self.assertEqual(resp["action"], "close")
    self.assertEqual(len(self.dm.tree), 0)

  def test_retv_11_escape_navigation(self):
    # Drill down into cluster
    self.fetcher.handle_rofi_request({"retv": 1, "info": "cluster:A1"})
    self.assertEqual(self.fetcher.rofi_context, ["A1"])

    # Escape pops context back to root
    resp = self.fetcher.handle_rofi_request({"retv": 11})
    self.assertEqual(resp["action"], "render")
    self.assertEqual(self.fetcher.rofi_context, [])

    # Escape at true root closes Rofi
    resp_close = self.fetcher.handle_rofi_request({"retv": 11})
    self.assertEqual(resp_close["action"], "close")

  def test_retv_11_escape_reverts_auto_descend(self):
    # If all notifications were in A1, auto_descend puts user inside A1 initially
    dm = DataManager([DummyConfig], "/dev/null")
    now = time.time_ns()
    dm.add_notification(Notification(1, "A1", "i", "1", "b", [], now, 1))
    fetcher = NotificationFetcher(dm, self.gui, start_ipc=False)
    fetcher.rofi_context = []
    fetcher.rofi_auto_descend = True

    # Escape when auto_descend is active reverts to root cluster view
    resp = fetcher.handle_rofi_request({"retv": 11})
    self.assertEqual(resp["action"], "render")
    self.assertFalse(fetcher.rofi_auto_descend)

    # Next Escape closes
    resp2 = fetcher.handle_rofi_request({"retv": 11})
    self.assertEqual(resp2["action"], "close")

  def test_retv_12_select_alt_cluster_best(self):
    # Shift+Return on cluster A1 invokes default action on its best notification
    resp = self.fetcher.handle_rofi_request({"retv": 12, "info": "cluster:A1"})
    self.assertEqual(resp["action"], "close")
    self.fetcher.ActionInvoked.assert_called_once_with(2, "default")
    self.fetcher.NotificationClosed.assert_called_once_with(2, 2)
    self.assertNotIn(2, self.dm.map)

  def test_retv_13_delete_alt_cluster_leaf(self):
    # Shift+Delete on cluster A1 deletes only the best notification (2), leaves 1
    resp = self.fetcher.handle_rofi_request({"retv": 13, "info": "cluster:A1"})
    self.assertEqual(resp["action"], "render")
    self.assertTrue(resp["keep_selection"])
    self.fetcher.NotificationClosed.assert_called_once_with(2, 2)
    self.assertNotIn(2, self.dm.map)
    self.assertIn(1, self.dm.map)

  def test_toggle_show_notifications(self):
    # Rofi not running: calls launch_script_mode
    self.gui.is_running.return_value = False
    self.fetcher.ShowNotifications()
    self.gui.launch_script_mode.assert_called_once()

    # Rofi already running: toggles off
    self.gui.is_running.return_value = True
    self.fetcher.ShowNotifications()
    self.gui.close.assert_called_once()


if __name__ == "__main__":
  unittest.main()
