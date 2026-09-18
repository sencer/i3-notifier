import unittest

from i3notifier.notification import Notification


from datetime import datetime

class TestNotificaton(unittest.TestCase):
  _notification = Notification(
    1, "app", "icon", "summary", "body", ["default"], 1595608250375722880, 1
  )

  def test_format(self):
    time_str = datetime.fromtimestamp(self._notification.created_at // 1e9).strftime("%H:%M")
    expected = (
      f"<b>summary</b> <small>{time_str}</small><small> app</small>\n<i>body</i>\x00icon\x1ficon".encode("utf-8")
    )
    self.assertEqual(
      self._notification.formatted(),
      expected,
    )


if __name__ == "__main__":
  unittest.main()
