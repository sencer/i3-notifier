import json
import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from i3notifier.config import Config
from i3notifier.data_manager import DataManager
from i3notifier.notification import Notification


class DummyConfig(Config):
  def get_keys(notification):
    return (notification.app_name, notification.summary)


class TestDataManager(unittest.TestCase):
  def __init__(self, *args, **kwargs):
    super(TestDataManager, self).__init__(*args, **kwargs)
    self.notifications = [
      Notification(1, "A3", "icon", "1", "113", ["dflt"], 1595608250375722879, 1),
      Notification(2, "A1", "icon", "1", "111", ["dflt"], 1595608250375722880, 1),
      Notification(3, "A1", "icon", "2", "121", ["dflt"], 1595608250375722881, 1),
      Notification(4, "A1", "icon", "1", "112", ["dflt"], 1595608250375722882, 1),
      Notification(5, "A2", "icon", "1", "211", ["dflt"], 1595608250375722884, 1),
      Notification(6, "A2", "icon", "2", "212", ["dflt"], 1595608250375722885, 1),
      Notification(7, "A1", "icon", "1", "113", ["dflt"], 1595608250375722886, 1),
    ]

    self.dm = DataManager([DummyConfig], "/dev/null")
    for notification in self.notifications:
      self.dm.add_notification(notification)

  def test_get_context_by_id(self):
    self.assertIs(
      self.dm.get_context_by_id(7),
      self.dm.tree.notifications["A1"].notifications["1"],
    )

  def test_get_context(self):
    self.assertIs(
      self.dm.get_context(("A1", "1")),
      self.dm.tree.notifications["A1"].notifications["1"],
    )

  def test_get_nocontext(self):
    self.assertIs(self.dm.get_context(), self.dm.tree)

  def test_leafs(self):
    self.assertCountEqual(self.dm.tree.leafs(), self.notifications)
    self.assertCountEqual(
      self.dm.get_context(("A1", "1")).leafs(),
      [
        self.notifications[1],
        self.notifications[3],
        self.notifications[6],
      ],
    )

  def test_add_notification(self):
    self.assertEqual(len(self.dm.tree), 7)
    self.assertEqual(len(self.dm.get_context(("A2",))), 2)
    self.assertIs(self.dm.tree.best, self.notifications[-1])

    notification = Notification(
      8, "A2", "icon", "1", "212", ["dflt"], 1595608250375722891, 1
    )

    self.dm.add_notification(notification)
    self.assertEqual(len(self.dm.tree), 8)
    self.assertEqual(len(self.dm.tree.notifications["A2"]), 3)
    self.assertIs(self.dm.get_context().best, notification)
    self.assertIs(self.dm.get_context(("A2",)).best, notification)

  def test_overwrite_notification(self):
    notification = Notification(
      3, "A1", "icon", "1", "212", ["dflt"], 1595608250375722891, 1
    )

    self.dm.add_notification(notification)
    self.assertEqual(len(self.dm.get_context()), len(self.notifications))
    self.assertEqual(len(self.dm.get_context(("A1",))), 4)
    self.assertIs(self.dm.get_context().best, notification)
    self.assertIs(self.dm.get_context(("A1",)).best, notification)

  def test_remove_notification(self):
    self.assertEqual(len(self.dm.get_context(("A1",))), 4)
    self.assertEqual(len(self.dm.tree), len(self.notifications))

    self.assertIs(self.dm.get_context().best, self.notifications[6])
    self.assertIs(self.dm.get_context(("A1",)).best, self.notifications[6])

    self.dm.remove_notification("1", ("A1",))

    self.assertEqual(len(self.dm.get_context(("A1",))), 1)
    self.assertEqual(len(self.dm.tree), 4)

    self.assertIs(self.dm.tree.best, self.notifications[5])
    self.assertIs(self.dm.get_context(("A1",)).best, self.notifications[2])

  def test_remove_notification_integer(self):
    self.assertEqual(len(self.dm.get_context(("A1",))), 4)
    self.assertEqual(len(self.dm.tree), 7)

    self.assertIs(self.dm.get_context().best, self.notifications[6])
    self.assertIs(self.dm.get_context(("A1",)).best, self.notifications[6])

    self.dm.remove_notification(7)

    self.assertEqual(len(self.dm.get_context(("A1",))), 3)
    self.assertEqual(len(self.dm.tree), 6)

    self.assertIs(self.dm.tree.best, self.notifications[5])
    self.assertIs(self.dm.get_context(("A1",)).best, self.notifications[3])

  def test_remove_shortcutted(self):
    self.dm.remove_notification(1)
    self.assertCountEqual(self.dm.tree.leafs(), self.notifications[1:])

    self.assertEqual(len(self.dm.tree), 6)
    self.assertNotIn("A3", self.dm.tree.notifications)

  def test_get_context_no_auto_descend(self):
    self.assertIs(
      self.dm.get_context(("A3",), auto_descend=False),
      self.dm.tree.notifications["A3"],
    )

  def test_get_context_auto_descend_default(self):
    self.assertIs(
      self.dm.get_context(("A3",)),
      self.dm.tree.notifications["A3"].notifications["1"],
    )


class TestPersistence(unittest.TestCase):
  def setUp(self):
    import tempfile
    self.temp_dir = tempfile.TemporaryDirectory()
    self.dump_path = os.path.join(self.temp_dir.name, "dump")

  def tearDown(self):
    self.temp_dir.cleanup()

  def test_dump_null_path(self):
    dm = DataManager([DummyConfig], "/dev/null")
    n = Notification(1, "A", "icon", "s", "b", ["d"], 1000)
    dm.add_notification(n)
    dm.remove_notification(1)
    dm.dump()
    self.assertEqual(len(dm.tree), 0)

  def test_dump_and_reload_atomic(self):
    dm1 = DataManager([DummyConfig], self.dump_path)
    n1 = Notification(1, "App1", "icon", "s1", "b1", ["d"], 1000)
    n2 = Notification(2, "App2", "icon", "s2", "b2", ["d"], 2000)
    dm1.add_notification(n1)
    dm1.add_notification(n2)

    self.assertTrue(os.path.exists(self.dump_path))
    tmp_files = [f for f in os.listdir(self.temp_dir.name) if f.endswith(".tmp")]
    self.assertEqual(len(tmp_files), 0)

    dm2 = DataManager([DummyConfig], self.dump_path)
    self.assertEqual(len(dm2.tree), 2)
    self.assertIn(1, dm2.map)
    self.assertIn(2, dm2.map)

  def test_remove_persists_immediately(self):
    dm = DataManager([DummyConfig], self.dump_path)
    n = Notification(1, "App", "icon", "s", "b", ["d"], 1000)
    dm.add_notification(n)

    with open(self.dump_path, "r") as f:
      data = json.load(f)
    self.assertEqual(len(data), 1)

    dm.remove_notification(1)

    with open(self.dump_path, "r") as f:
      data = json.load(f)
    self.assertEqual(len(data), 0)

  def test_expired_notifications_filtered_on_load(self):
    import time
    now = time.time_ns()
    n_expired = Notification(
      1, "App", "icon", "s1", "b1", ["d"], now - 20_000_000_000,
      expires_at=now - 10_000_000_000, expires=True
    )
    n_future = Notification(
      2, "App", "icon", "s2", "b2", ["d"], now,
      expires_at=now + 10_000_000_000, expires=True
    )
    n_persistent = Notification(
      3, "App", "icon", "s3", "b3", ["d"], now,
      expires_at=None, expires=False
    )

    with open(self.dump_path, "w") as f:
      import json
      json.dump([n_expired.to_dict(), n_future.to_dict(), n_persistent.to_dict()], f)

    dm = DataManager([DummyConfig], self.dump_path)
    self.assertNotIn(1, dm.map)
    self.assertIn(2, dm.map)
    self.assertIn(3, dm.map)
    self.assertEqual(len(dm.tree), 2)


class TestNotificationFetcher(unittest.TestCase):
  @patch("i3notifier.notification_fetcher.Gio")
  def test_fetcher_id_and_timer_restoration(self, mock_gio):
    from unittest.mock import MagicMock
    from i3notifier.notification_fetcher import NotificationFetcher

    class ExpConfig(Config):
      expires = True

    now = time.time_ns()
    n1 = Notification(10, "A", "i", "s", "b", [], now, expires_at=now + 5_000_000_000, expires=True)
    n2 = Notification(3, "A", "i", "s", "b", [], now, expires_at=None, expires=False)
    dm = DataManager([ExpConfig], "/dev/null")
    dm.add_notification(n1)
    dm.add_notification(n2)

    fetcher = NotificationFetcher(dm, MagicMock())
    self.assertEqual(fetcher._id, 11)
    self.assertIsNotNone(n1.timer)
    dm.cancel_timers()

  @patch("i3notifier.notification_fetcher.Gio")
  def test_id_collision_skip(self, mock_gio):
    from unittest.mock import MagicMock
    from i3notifier.notification_fetcher import NotificationFetcher

    dm = DataManager([DummyConfig], "/dev/null")
    fetcher = NotificationFetcher(dm, MagicMock())
    self.assertEqual(fetcher._id, 1)

    # Simulate an app inserting an ID ahead of sequence (replaces_id)
    n_custom = Notification(1, "A", "i", "s", "b", [], time.time_ns())
    dm.add_notification(n_custom)

    # Next Notify without replaces_id should skip 1 and take 2
    fetcher.connection = MagicMock()
    assigned_id = fetcher.Notify("A", 0, "i", "s", "b", [], {}, -1)
    self.assertEqual(assigned_id, 2)
    self.assertIn(1, dm.map)
    self.assertIn(2, dm.map)

  @patch("i3notifier.notification_fetcher.Gio")
  def test_fetcher_immediate_expiration_on_startup(self, mock_gio):
    from unittest.mock import MagicMock
    from i3notifier.notification_fetcher import NotificationFetcher

    class ExpConfig(Config):
      expires = True

    now = time.time_ns()
    # Notification that expires immediately on startup (delay <= 0)
    n = Notification(5, "A", "i", "s", "b", [], now, expires_at=now - 1_000_000, expires=True)
    dm = DataManager([ExpConfig], "/dev/null")
    dm.map[5] = ("A", "b")
    DataManager._recursive_add_notification(dm.tree, n, ["A", "b", 5])

    fetcher = NotificationFetcher(dm, MagicMock())
    # Should not crash with AttributeError and should remove expired notification
    self.assertNotIn(5, dm.map)
    self.assertEqual(len(dm.tree), 0)


if __name__ == "__main__":
  unittest.main()
