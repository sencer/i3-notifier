import unittest

from i3notifier.config import Config
from i3notifier.data_manager import DataManager
from i3notifier.notification import Notification, NotificationCluster


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
            [self.notifications[1], self.notifications[3], self.notifications[6],],
        )

    def test_add_notification(self):
        self.assertEqual(len(self.dm.tree), 7)
        self.assertEqual(len(self.dm.get_context(("A2",))), 2)
        self.assertIs(self.dm.tree.last, self.notifications[-1])

        notification = Notification(
            8, "A2", "icon", "1", "212", ["dflt"], 1595608250375722891, 1
        )

        self.dm.add_notification(notification)
        self.assertEqual(len(self.dm.tree), 8)
        self.assertEqual(len(self.dm.tree.notifications["A2"]), 3)
        self.assertIs(self.dm.get_context().last, notification)
        self.assertIs(self.dm.get_context(("A2",)).last, notification)

    def test_overwrite_notification(self):
        notification = Notification(
            3, "A1", "icon", "1", "212", ["dflt"], 1595608250375722891, 1
        )

        self.dm.add_notification(notification)
        self.assertEqual(len(self.dm.get_context()), len(self.notifications))
        self.assertEqual(len(self.dm.get_context(("A1",))), 4)
        self.assertIs(self.dm.get_context().last, notification)
        self.assertIs(self.dm.get_context(("A1",)).last, notification)

    def test_remove_notification(self):
        self.assertEqual(len(self.dm.get_context(("A1",))), 4)
        self.assertEqual(len(self.dm.tree), len(self.notifications))

        self.assertIs(self.dm.get_context().last, self.notifications[6])
        self.assertIs(self.dm.get_context(("A1",)).last, self.notifications[6])

        self.dm.remove_notification("1", ("A1",))

        self.assertEqual(len(self.dm.get_context(("A1",))), 1)
        self.assertEqual(len(self.dm.tree), 4)

        self.assertIs(self.dm.tree.last, self.notifications[5])
        self.assertIs(self.dm.get_context(("A1",)).last, self.notifications[2])

    def test_remove_notification_integer(self):
        self.assertEqual(len(self.dm.get_context(("A1",))), 4)
        self.assertEqual(len(self.dm.tree), 7)

        self.assertIs(self.dm.get_context().last, self.notifications[6])
        self.assertIs(self.dm.get_context(("A1",)).last, self.notifications[6])

        self.dm.remove_notification(7)

        self.assertEqual(len(self.dm.get_context(("A1",))), 3)
        self.assertEqual(len(self.dm.tree), 6)

        self.assertIs(self.dm.tree.last, self.notifications[5])
        self.assertIs(self.dm.get_context(("A1",)).last, self.notifications[3])

    def test_remove_shortcutted(self):
        self.dm.remove_notification(1)
        self.assertCountEqual(self.dm.tree.leafs(), self.notifications[1:])

        self.assertEqual(len(self.dm.tree), 6)
        self.assertNotIn("A3", self.dm.tree.notifications)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
