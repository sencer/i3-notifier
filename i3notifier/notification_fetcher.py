import enum
import logging
import os.path
import threading
import time

from gi.repository import GLib, Gio
import xdg.BaseDirectory
from xdg.DesktopEntry import DesktopEntry

from i3notifier.notification import Notification
from i3notifier.rofi_gui import Operation

BUS_NAME = "org.freedesktop.Notifications"
OBJECT_PATH = "/org/freedesktop/Notifications"
INTERFACE_NAME = "org.freedesktop.Notifications"

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


class NotificationUpdateMode(enum.Enum):
  ADDED = 0
  DELETED = 1
  MANUAL = 2


INTROSPECTION_XML = """
<node>
  <interface name="org.freedesktop.Notifications">
    <method name="GetCapabilities">
      <arg direction="out" type="as"/>
    </method>
    <method name="Notify">
      <arg direction="in" type="s" name="app_name"/>
      <arg direction="in" type="u" name="replaces_id"/>
      <arg direction="in" type="s" name="app_icon"/>
      <arg direction="in" type="s" name="summary"/>
      <arg direction="in" type="s" name="body"/>
      <arg direction="in" type="as" name="actions"/>
      <arg direction="in" type="a{sv}" name="hints"/>
      <arg direction="in" type="i" name="expire_timeout"/>
      <arg direction="out" type="u" name="id"/>
    </method>
    <method name="CloseNotification">
      <arg direction="in" type="u" name="id"/>
    </method>
    <method name="GetServerInformation">
      <arg direction="out" type="s" name="name"/>
      <arg direction="out" type="s" name="vendor"/>
      <arg direction="out" type="s" name="version"/>
      <arg direction="out" type="s" name="spec_version"/>
    </method>
    <signal name="NotificationClosed">
      <arg type="u" name="id"/>
      <arg type="u" name="reason"/>
    </signal>
    <signal name="ActionInvoked">
      <arg type="u" name="id"/>
      <arg type="s" name="action_key"/>
    </signal>

    <!-- Custom methods -->
    <method name="DumpNotifications">
      <arg direction="out" type="s"/>
    </method>
    <method name="ShowNotificationCount">
      <arg direction="out" type="u"/>
      <arg direction="out" type="u"/>
    </method>
    <method name="ShowNotifications"/>
    <method name="SignalNotificationCount"/>
    <method name="Quit"/>

    <signal name="NotificationsUpdated">
      <arg type="u" name="mode"/>
      <arg type="u" name="num"/>
      <arg type="u" name="urgency"/>
      <arg type="s" name="single_line"/>
    </signal>
  </interface>
</node>
"""


class NotificationFetcher:
  def __init__(self, dm, gui):
    self.dm = dm
    self.gui = gui
    self.context = []
    self._id = 1

    if len(self.dm.tree):
      self._id = self.dm.tree.best.id + 1

    self.node_info = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION_XML)
    self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    self.connection.register_object(
      OBJECT_PATH,
      self.node_info.interfaces[0],
      self.handle_method_call,
      None,
      None,
    )

    Gio.bus_own_name_on_connection(
      self.connection, BUS_NAME, Gio.BusNameOwnerFlags.NONE, None, None
    )

  def handle_method_call(
    self,
    connection,
    sender,
    object_path,
    interface_name,
    method_name,
    parameters,
    invocation,
  ):
    args = parameters.unpack()
    if method_name == "GetCapabilities":
      invocation.return_value(
        GLib.Variant(
          "(as)", [["actions", "body", "body-markup", "icon-static", "persistence"]]
        )
      )
    elif method_name == "Notify":
      (
        app_name,
        replaces_id,
        app_icon,
        summary,
        body,
        actions,
        hints,
        expire_timeout,
      ) = args
      id = self.Notify(
        app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout
      )
      invocation.return_value(GLib.Variant("(u)", [id]))
    elif method_name == "CloseNotification":
      (id,) = args
      self.CloseNotification(id)
      invocation.return_value(None)
    elif method_name == "GetServerInformation":
      invocation.return_value(
        GLib.Variant(
          "(ssss)", ("i3notifier", "github.com/sencer/i3-notifier", "0.23", "1.2")
        )
      )
    elif method_name == "DumpNotifications":
      res = self.DumpNotifications()
      invocation.return_value(GLib.Variant("(s)", [res]))
    elif method_name == "ShowNotificationCount":
      count, urgency = self.ShowNotificationCount()
      invocation.return_value(GLib.Variant("(uu)", [count, urgency]))
    elif method_name == "ShowNotifications":
      self.ShowNotifications()
      invocation.return_value(None)
    elif method_name == "SignalNotificationCount":
      self.SignalNotificationCount()
      invocation.return_value(None)
    elif method_name == "Quit":
      invocation.return_value(None)
      self.Quit()

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
      # Fix mixed units: expire_timeout is in ms, created_at is in ns
      notification.expires_at = notification.created_at + (expire_timeout * 1000000)

    if "urgency" in hints:
      urgency = hints["urgency"]
      if hasattr(urgency, "real"):
        notification.urgency = int(urgency.real)
      else:
        notification.urgency = int(urgency)

    self.dm.add_notification(notification)

    if notification.expires and notification.expires_at:
      # Fix mixed units: (ns - ns) / 1e9 = seconds
      delay = (notification.expires_at - notification.created_at) / 1000000000
      notification.timer = threading.Timer(
        delay,
        self._remove_notification,
        (notification.id, RemoveReason.EXPIRED),
      )
      notification.timer.start()

    self._notifications_updated(NotificationUpdateMode.ADDED.value)
    return id

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

  def DumpNotifications(self):
    self.dm.dump()
    return str(self.dm.tree)

  def ShowNotificationCount(self):
    return len(self.dm.tree), self.dm.tree.urgency or 0

  def ShowNotifications(self):
    self.context = []
    if len(self.dm.tree) > 0:
      self._show_notifications()

  def SignalNotificationCount(self):
    self._notifications_updated(NotificationUpdateMode.MANUAL.value)

  def Quit(self):
    logger.info("Quit requested via DBus.")
    self.dm.dump()
    self.dm.cancel_timers()
    import sys

    sys.exit(0)

  # Signals

  def ActionInvoked(self, id, action):
    logger.info(f"ActionInvoked with action {action} signalled for {id}.")
    self.connection.emit_signal(
      None,
      OBJECT_PATH,
      INTERFACE_NAME,
      "ActionInvoked",
      GLib.Variant("(us)", (id, action)),
    )

  def NotificationClosed(self, id, reason):
    logger.info(f"NotificationClosed signalled for {id} due to {reason}.")
    self.connection.emit_signal(
      None,
      OBJECT_PATH,
      INTERFACE_NAME,
      "NotificationClosed",
      GLib.Variant("(uu)", (id, reason)),
    )

  def NotificationsUpdated(self, mode, num, urgency, single_line):
    logger.info("Notifications updated.")
    self.connection.emit_signal(
      None,
      OBJECT_PATH,
      INTERFACE_NAME,
      "NotificationsUpdated",
      GLib.Variant("(uuus)", (mode, num, urgency, single_line)),
    )

  # Internal methods

  def _notifications_updated(self, mode):
    self.NotificationsUpdated(
      mode,
      len(self.dm.tree),
      (self.dm.tree.urgency or 0),
      self.dm.last.single_line() if self.dm.last else "",
    )

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
    self._notifications_updated(NotificationUpdateMode.DELETED.value)
    return self._update_context()

  def _show_notifications(self, row=0, auto_descend=True):
    notifications = self.dm.get_context(self.context, auto_descend=auto_descend).notifications

    items = sorted(
      notifications.items(), key=lambda x: (-x[1].urgency, -x[1].best.created_at)
    )

    selected, op = self.gui.show_notifications([item[1] for item in items], row)
    logger.info(
      f"Selection is {None if selected is None else items[selected][0]}"
      f", operation is {op}."
    )

    if op == Operation.EXIT_COMPLETELY:
      return

    if op == Operation.EXIT:
      if self.context:
        self.context.pop()
        self._show_notifications()
      else:
        actual_root = self.dm.get_context([], auto_descend=False)
        current_root = self.dm.get_context(self.context, auto_descend=auto_descend)
        
        if current_root is not actual_root and auto_descend:
          self._show_notifications(auto_descend=False)
        else:
          return
      return

    if selected is None:
      logger.info(f"DEBUG THIS {items}")
      return

    key, notification = items[selected]

    if op == Operation.SELECT or op == Operation.SELECT_ALT:
      if len(notification) == 1 or op == Operation.SELECT_ALT:
        logger.info("Selection is a singleton. Invoking default action.")
        self.context = self.dm.map[notification.best.id]

        if self._process_hooks(notification.best, "pre_action_hooks"):
          self.ActionInvoked(notification.best.id, "default")
        else:
          logger.info(f"Skipping action for {notification.id}.")

        if self._process_hooks(notification.best, "post_action_hooks"):
          self._remove_notification(notification.best.id, RemoveReason.ACTION_INVOKED)
          self.NotificationClosed(notification.best.id, 2)
        else:
          logger.info(
            f"Skipping CloseNotification (after action) for {notification.id}."
          )
      else:
        logger.info("Selection is a cluster. Expanding.")
        self.context.append(key)
        self._show_notifications()
    elif op == Operation.DELETE or op == Operation.DELETE_ALT:
      key_ = key if op == Operation.DELETE else notification.best.id
      context_changed = self._remove_notification(key_, RemoveReason.USER_DELETED)

      row = 0 if context_changed else selected - (selected == len(notifications))

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
