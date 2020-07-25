import unittest

from i3notifier.notification import Notification, NotificationCluster


class TestNotificaton(unittest.TestCase):

    _notification = Notification(
        1, "app", "icon", "summary", "body", ["default"], 1595608250375722880, 1
    )

    def test_format(self):
        self.assertEqual(
            self._notification.formatted(),
            b"<b>summary</b> <small>app</small>\n<i>body</i>",
        )


if __name__ == "__main__":
    unittest.main()
