import unittest

from i3notifier.notification import Notification, NotificationCluster


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

class TestNotificationCluster(unittest.TestCase):
  def test_empty_cluster_format(self):
    cluster = NotificationCluster()
    self.assertEqual(cluster.formatted(), b"")

  def test_single_item_cluster_format(self):
    cluster = NotificationCluster()
    n = Notification(1, "app", "icon", "summary", "body", ["default"], 1595608250375722880, 1)
    cluster.add(1, n)
    self.assertEqual(cluster.formatted(), n.formatted())

  def test_multi_item_cluster_format(self):
    cluster = NotificationCluster()
    n1 = Notification(1, "app", "icon", "summary1", "body1", ["default"], 1595608250375722880, 1)
    n2 = Notification(2, "app", "icon", "summary2", "body2", ["default"], 1595608250375722890, 1)
    cluster.add(1, n1)
    cluster.add(2, n2)
    self.assertIn(b"app (2)", cluster.formatted())


if __name__ == "__main__":
  unittest.main()
