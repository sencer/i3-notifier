import os.path
import time

import dbus
import dbus.service

import xdg.BaseDirectory
from xdg.DesktopEntry import DesktopEntry

from .notification import Notification
from .rofi_gui import Operation

DBUS_PATH = "org.freedesktop.Notifications"


def xdg_name_and_icon(app):
    entry = DesktopEntry()
    for directory in xdg.BaseDirectory.xdg_data_dirs:
        path = os.path.join(directory, "applications", f"{app}.desktop")
        if os.path.exists(path):
            entry.parse(path)
            return entry.getName(), entry.getIcon()
    return None, None


class NotificationFetcher(dbus.service.Object):
    _id = 1

    def __init__(self, dm, gui, desktop=None):
        self.dm = dm
        self.gui = gui
        self.desktop = desktop
        name = dbus.service.BusName(DBUS_PATH, dbus.SessionBus())
        super().__init__(name, "/org/freedesktop/Notifications")

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
            notification.expire_at = notification.created_at + expire_timeout

        if "urgency" in hints:
            notification.urgency = int(hints["urgency"]) if isinstance(hints["urgency"], str) else hints["urgency"].real

        self.dm.add_notification(notification)
        return id

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="as")
    def GetCapabilities(self):
        return [
            "actions",
            "body",
            "body-hyperlinks",
            "body-images",
            "body-markup",
            "icon-static",
        ]

    @dbus.service.method(DBUS_PATH, in_signature="u", out_signature="")
    def CloseNotification(self, id):
        self.dm.remove_notification(id)
        self._update_context()
        self.NotificationClosed(id, 3)

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="ssss")
    def GetServerInformation(self):
        return "notification_fetcher", "github.com/sencer", "0.0.0", "1"

    def _update_context(self):
        new_context = []
        p = self.dm.tree
        for key in self.context:
            if key not in p.notifications:
                break
            new_context.append(key)
            p = p.notifications[key]
        self.context = new_context

    def _show_notifications(self):
        notifications = self.dm.get_context(self.context).notifications

        items = [
            (k, v) if len(v) > 1 else (v.last().id, v.last())
            for k, v in notifications.items()
        ]

        selected, op = self.gui.show_notifications([item[1] for item in items])

        if op == Operation.EXIT:
            if self.context:
                self.context.pop()
                self._show_notifications()
                return

        key, notification = items[selected]

        do_action = isinstance(notification, Notification)
        if do_action:
            self.context = self.dm.map[notification.id]

        if op == Operation.SELECT:
            if do_action and self.desktop:
                closure = lambda: self.ActionInvoked(key, "default")
                self.desktop.process_action(closure)
            else:
                self.context.append(key)
                self._show_notifications()
        elif op == Operation.DELETE:
            self.dm.remove_notification(key, self.context)
            self._update_context()

            if len(self.dm.tree):
                self._show_notifications()

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="")
    def ShowNotifications(self):
        self.context = []
        self._show_notifications()

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="u")
    def ShowNotificationCount(self):
        return len(self.dm.tree)

    @dbus.service.method(DBUS_PATH, in_signature="", out_signature="s")
    def DumpNotifications(self):
        return str(self.dm.tree)

    @dbus.service.signal(DBUS_PATH, signature="uu")
    def NotificationClosed(self, id, reason):
        print(f"Closed notification {id} due to {reason}")

    @dbus.service.signal(DBUS_PATH, signature="us")
    def ActionInvoked(self, id, action):
        print(f"Action {action} on {id}")
