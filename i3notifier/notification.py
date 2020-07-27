import copy
import itertools
from enum import IntEnum

from .config import Config


class Urgency(IntEnum):

    LOW = 0
    MEDIUM = 1
    CRITICAL = 2


class Notification:
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
        urgency=None,
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

    def formatted(self):
        return self.config.format_notification(self)

    def keys(self):
        return self.config.get_keys(self)

    def closeable(self):
        return self.config.closeable(self)

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

    def last(self):
        return self

    def leafs(self):
        return [self]

    def __repr__(self):
        return f"{self.app_name} {self.summary} {self.created_at} {self.urgency}"

    def __str__(self):
        return self.__repr__()


class NotificationCluster:
    def __init__(self):
        self.notifications = dict()
        self._last = None
        self._len = 0
        self._urgency = None

    @property
    def urgency(self):

        self._urgency = self._urgency or (
            max(
                notification.urgency or 0
                for notification in self.notifications.values()
            )
            if self.notifications
            else None
        )
        return self._urgency

    def formatted(self):
        if len(self) == 1:
            return self.last().formatted()

        dummy = copy.deepcopy(self.last())
        dummy.app_name = f"{dummy.app_name} ({len(self)})"
        return dummy.formatted()

    def reset(self):
        self._len = 0
        self._urgency = None
        self._last = None

    def add(self, key, notification):

        if self._last is None or notification.urgency >= self.last().urgency:
            self._last = notification
        self._urgency = self.last().urgency
        self._len += 1

        if isinstance(key, int):
            self.notifications[key] = notification

    def remove(self, key):
        if self.urgency == self.notifications[key].urgency:
            self._urgency = None

        if self.notifications[key] == self.last():
            self._last = None

        self._len -= len(self.notifications[key])

        del self.notifications[key]

    def last(self):
        # This is called last for historical reasons, where I represented a cluster
        # by the last notification in it. Now urgency trumps creation time. So this
        # is kind of 'best' rather than 'last'
        self._last = self._last or (
            max(
                self.notifications.values(),
                key=lambda x: (x.urgency, x.last().created_at),
            ).last()
            if self.notifications
            else None
        )
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
