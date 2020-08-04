import copy
import itertools
from enum import IntEnum

from .config import Config


class Urgency(IntEnum):

    LOW = 0
    MEDIUM = 1
    CRITICAL = 2


class Notification:
    __slots__ = (
        "id",
        "app_name",
        "app_icon",
        "body",
        "summary",
        "actions",
        "created_at",
        "expires_at",
        "urgency",
        "config",
        "timer",
    )

    def __init__(
        self,
        id,
        app_name,
        app_icon,
        summary,
        body,
        actions,
        created_at,
        expires_at=None,
        urgency=0,
    ):
        self.id = id
        self.app_name = app_name
        self.app_icon = app_icon
        self.summary = summary
        self.body = body
        self.actions = actions
        self.created_at = created_at
        self.expires_at = expires_at
        self.urgency = urgency
        self.config = Config
        self.timer = None

    @property
    def pre_action_hooks(self):
        return self.config.pre_action_hooks

    @property
    def post_action_hooks(self):
        return self.config.post_action_hooks

    @property
    def pre_close_hooks(self):
        return self.config.pre_close_hooks

    @property
    def post_close_hooks(self):
        return self.config.post_close_hooks

    @property
    def expires(self):
        return self.config.expires

    def formatted(self):
        return self.config.format_notification(self)

    def keys(self):
        return self.config.get_keys(self)

    def strip(self):
        return Notification(
            self.id,
            self.app_name,
            self.app_icon,
            self.summary,
            self.body,
            self.actions,
            self.created_at,
            self.expires_at,
            self.urgency,
        )

    def __len__(self):
        return 1

    @property
    def last(self):
        return self

    def leafs(self):
        return [self]

    def __repr__(self):
        return (
            "<Notification: "
            f"id:{self.id} "
            f'app_name:"{self.app_name}" '
            f'app_icon:"{self.app_icon}" '
            f'summary:"{self.summary}" '
            f'body:"{self.body}" '
            f"actions:{self.actions} "
            f"urgency:{self.urgency} "
            f"created_at:{self.created_at} "
            f"expires_at:{self.expires_at}>"
        )

    def __str__(self):
        return self.__repr__()


class NotificationCluster:
    __slots__ = "notifications", "_last", "_len", "_urgency"

    def __init__(self):
        self.notifications = dict()
        self._last = None
        self._len = 0
        self._urgency = None

    @property
    def urgency(self):

        if self._urgency is None and self.notifications:
            self._urgency = self.last.urgency

        return self._urgency or 0

    def formatted(self):
        if len(self) == 1:
            return self.last.formatted()

        dummy = self.last.strip()
        dummy.app_name = f"{dummy.app_name} ({len(self)})"
        dummy.config = self.last.config
        return dummy.formatted()

    def reset(self):
        self._len = 0
        self._urgency = None
        self._last = None

    def add(self, key, notification):

        if self._last is None or notification.urgency >= self.last.urgency:
            self._last = notification
        self._urgency = self.last.urgency
        self._len += 1

        if isinstance(key, int):
            self.notifications[key] = notification

    def remove(self, key):
        if self.urgency == self.notifications[key].urgency:
            self._urgency = None

        if self.notifications[key] == self.last:
            self._last = None

        self._len -= len(self.notifications[key])

        del self.notifications[key]

    @property
    def last(self):
        # This is called last for historical reasons, where I represented a cluster
        # by the last notification in it. Now urgency trumps creation time. So this
        # is kind of 'best' rather than 'last'
        if self._last is None and self.notifications:
            self._last = max(
                self.notifications.values(),
                key=lambda x: (x.urgency, x.last.created_at),
            ).last

        return self._last

    def __len__(self):
        self._len = self._len or sum(len(n) for n in self.notifications.values())
        return self._len or 0

    def leafs(self):
        return list(
            itertools.chain.from_iterable(
                v.leafs() for v in self.notifications.values()
            )
        )

    def __str__(self):
        return str(self.notifications)

    def __repr__(self):
        return repr(self.notifications)
