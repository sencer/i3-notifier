import enum
import logging
import os.path
import threading
import time

import dbus
import dbus.service

import xdg.BaseDirectory
from xdg.DesktopEntry import DesktopEntry

from .notification import Notification
from .rofi_gui import Operation

DBUS_PATH = "org.freedesktop.Notifications"

logger = logging.getLogger(__name__)


def xdg_name_and_icon(app):
    entry = DesktopEntry()
    for directory in xdg.BaseDirectory.xdg_data_dirs:
        path = os.path.join(directory, "applications", f"{app}.desktop")
        if os.path.exists(path):
            entry.parse(path)
            return entry.getName(), entry.getIcon()
    return None, None


class RemoveReason(enum.Enum):
    APP_REQUESTED = 0
    USER_DELETED = 1
    ACTION_INVOKED = 2
    EXPIRED = 3


class NotificationFetcher(dbus.service.Object):
    __slots__ = "dm", "gui", "context"
    _id = 1

    def __init__(self, dm, gui):
        self.dm = dm
        self.gui = gui
        self.context = []

        if len(self.dm.tree):
            self._id = self.dm.tree.last.id + 1

        name = dbus.service.BusName(DBUS_PATH, dbus.SessionBus())
        super().__init__(name, "/org/freedesktop/Notifications")

    @dbus.service.method(DBUS_PATH, in_signature="u", out_signature="")
    def CloseNotification(self, id):

        notification = self.dm.get_context_by_id(id).notifications[id]
        logger.info(f"Received CloseNotification request for {notification}")

        if self._process_hooks(notification, "pre_close_hooks"):
            self.NotificationClosed(id, 3)
        else:
            logger.info(f"Didn't send NotificationClosed signal for {id}")

        if self._process_hooks(notification, "post_close_hooks"):
            self._remove_notification(id, RemoveReason.APP_REQUESTED)
        else:
            logger.info(f"Didn't delete notification {id}.")

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="s")
    def DumpNotifications(self):
        self.dm.dump()
        return str(self.dm.tree)

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="as")
    def GetCapabilities(self):
        return [
            "actions",
            "body",
            "body-markup",
            "icon-static",
            "persistence",
        ]

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="ssss")
    def GetServerInformation(self):
        return "i3notifier", "github.com/sencer/i3-notifier", "0.12", "1.2"

    @dbus.service.method(DBUS_PATH, in_signature="susssasa{ss}i", out_signature="u")
    def Notify(
        self,
        app_name,
        replaces_id,
        app_icon,
        summary,
        body,
        actions,
        hints,
        expire_timeout,
    ):
        logger.info(
            "Received notification:\n"
            f'app_name:"{app_name}" '
            f"replaces_id:{replaces_id} "
            f'app_icon:"{app_icon}" '
            f'summary:"{summary}" '
            f'body:"{body}" '
            f'actions:"{actions}" '
            f'hints:"{hints}" '
            f"expire_timeout:{expire_timeout}"
        )

        if replaces_id > 0:
            id = replaces_id
        else:
            id = self._id
            self._id += 1

        app = icon = None
        if "desktop-entry" in hints and not (app_name and app_icon):
            app, icon = xdg_name_and_icon(hints["desktop-entry"])
            app_name = app_name or app or hints["desktop-entry"].split(".")[-1]

        if not app_icon or app_icon.startswith("file://"):
            if icon:
                app_icon = icon
            elif "image-path" in hints:
                app_icon = hints["image-path"]

        notification = Notification(
            id=id,
            app_name=app_name,
            app_icon=app_icon,
            summary=summary,
            body=body,
            actions=actions,
            created_at=time.time_ns(),
        )

        if expire_timeout > 0:
            notification.expires_at = notification.created_at + expire_timeout

        if "urgency" in hints:
            notification.urgency = (
                int(hints["urgency"])
                if isinstance(hints["urgency"], str)
                else hints["urgency"].real
            )

        self.dm.add_notification(notification)

        if notification.expires and notification.expires_at:
            notification.timer = threading.Timer(
                (notification.expires_at - notification.created_at) / 1000,
                self._remove_notification,
                (notification.id, RemoveReason.EXPIRED),
            )
            notification.timer.start()

        self._notifications_updated()
        return id

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="uu")
    def ShowNotificationCount(self):
        return len(self.dm.tree), self.dm.tree.urgency or 0

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="")
    def ShowNotifications(self):
        self.context = []
        self._show_notifications()

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="")
    def SignalNotificationCount(self):
        self._notifications_updated()

    # Signals

    @dbus.service.signal(DBUS_PATH, signature="us")
    def ActionInvoked(self, id, action):
        logger.info(f"ActionInvoked with action {action} signalled for {id}.")

    @dbus.service.signal(DBUS_PATH, signature="uu")
    def NotificationClosed(self, id, reason):
        logger.info(f"NotificationClosed signalled for {id} due to {reason}.")

    @dbus.service.signal(DBUS_PATH, signature="uu")
    def NotificationsUpdated(self, num, urgency):
        logger.info(f"Notifications updated.")

    # Internal methods

    def _notifications_updated(self):
        self.NotificationsUpdated(len(self.dm.tree), self.dm.tree.urgency or 0)

    def _process_hooks(self, notification, hook_name):
        logger.info(f"Processing {hook_name}")
        ret = True

        for hook in getattr(notification, hook_name):
            logger.info(f"  > Hook {hook}")
            if hook == "ignore":
                ret = False
            else:
                hook(notification)

        return ret

    def _remove_notification(self, key, reason):
        logger.info(f"Attempting to remove notification {key} since {reason}")
        self.dm.remove_notification(key, self.context)
        self._notifications_updated()
        return self._update_context()

    def _show_notifications(self, row=0):
        notifications = self.dm.get_context(self.context).notifications

        items = sorted(
            [
                (k, v) if len(v) > 1 else (v.last.id, v.last)
                for k, v in notifications.items()
            ],
            key=lambda x: (-x[1].urgency, -x[1].last.created_at),
        )

        selected, op = self.gui.show_notifications([item[1] for item in items], row)
        logger.info(
            f"Selection is {None if selected is None else items[selected][0]}"
            f", operation is {op}."
        )

        if op == Operation.EXIT:
            if self.context:
                self.context.pop()
                self._show_notifications()
            return

        if selected is None:
            logger.info(f"DEBUG THIS {items}")
            return

        key, notification = items[selected]

        if op == Operation.SELECT:
            if isinstance(notification, Notification):
                logger.info("Selection is a singleton. Invoking default action.")
                self.context = self.dm.map[notification.id]

                if self._process_hooks(notification, "pre_action_hooks"):
                    self.ActionInvoked(notification.id, "default")
                else:
                    logger.info(f"Skipping action for {notification.id}.")

                if self._process_hooks(notification, "post_action_hooks"):
                    self._remove_notification(
                        notification.id, RemoveReason.ACTION_INVOKED
                    )
                    self.NotificationClosed(notification.id, 2)
                else:
                    logger.info(
                        f"Skipping CloseNotification (after action) for {notification.id}."
                    )
            else:
                logger.info("Selection is a cluster. Expanding.")
                self.context.append(key)
                self._show_notifications()
        elif op == Operation.DELETE:
            context_changed = self._remove_notification(key, RemoveReason.USER_DELETED)
            row = 0 if context_changed or len(notifications) == 1 else selected

            if len(self.dm.tree):
                self._show_notifications(row)

    def _update_context(self):
        new_context = []
        p = self.dm.tree
        for key in self.context:
            if key not in p.notifications:
                break
            new_context.append(key)
            p = p.notifications[key]
        if self.context == new_context:
            logger.info("Context did not change")
            return False

        logger.info("Context updated.")
        self.context = new_context
        return True
