import os
import unittest
from unittest.mock import MagicMock, patch

from i3notifier.rofi_gui import Operation, RofiGUI


class TestRofiGUI(unittest.TestCase):
  def test_theme_auto_append_rasi(self):
    gui = RofiGUI(theme="widget")
    theme_idx = gui._args.index("-theme")
    self.assertTrue(gui._args[theme_idx + 1].endswith(".rasi"))
    self.assertTrue(gui._args[theme_idx + 1].endswith("widget.rasi"))

  def test_theme_already_has_rasi(self):
    gui = RofiGUI(theme="widget.rasi")
    theme_idx = gui._args.index("-theme")
    self.assertTrue(gui._args[theme_idx + 1].endswith("widget.rasi"))
    self.assertFalse(gui._args[theme_idx + 1].endswith(".rasi.rasi"))

  @patch("subprocess.Popen")
  def test_show_notifications_communicates_and_parses_selection(self, mock_popen):
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (b"2\n", None)
    mock_proc.returncode = 0
    mock_popen.return_value = mock_proc

    gui = RofiGUI()
    mock_n = MagicMock()
    mock_n.formatted.return_value = b"test notification"

    sel, op = gui.show_notifications([mock_n], row=0)
    self.assertEqual(sel, 2)
    self.assertEqual(op, Operation.SELECT)
    mock_proc.communicate.assert_called_once_with(input=b"test notification")

  @patch("subprocess.Popen")
  def test_show_notifications_handles_unknown_exit_code(self, mock_popen):
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (b"", None)
    mock_proc.returncode = 127
    mock_popen.return_value = mock_proc

    gui = RofiGUI()
    sel, op = gui.show_notifications([], row=0)
    self.assertIsNone(sel)
    self.assertEqual(op, Operation.EXIT_COMPLETELY)

  @patch("subprocess.Popen")
  def test_show_notifications_handles_non_integer_stdout(self, mock_popen):
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (b"not-an-int\n", None)
    mock_proc.returncode = 1
    mock_popen.return_value = mock_proc

    gui = RofiGUI()
    sel, op = gui.show_notifications([], row=0)
    self.assertIsNone(sel)
    self.assertEqual(op, Operation.EXIT_COMPLETELY)


if __name__ == "__main__":
  unittest.main()
