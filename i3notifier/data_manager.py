import threading

from .notification import Notification, NotificationCluster


class DataManager(threading.Thread):
    def __init__(self, configs):
        self.lock = threading.Lock()
        self.tree = NotificationCluster()
        self.map = dict()
        self.configs = configs

        super().__init__()

    def _recursive_add_notification(cluster, notification, keys, i=0):
        if i == len(keys):
            return

        if keys[i] not in cluster.notifications:
            cluster.notifications[keys[i]] = NotificationCluster()

        DataManager._recursive_add_notification(
            cluster.notifications[keys[i]], notification, keys, i + 1
        )
        cluster.add(keys[i], notification)

    def add_notification(self, notification):

        for config in self.configs:
            if config.should_apply(notification):
                config.update_notification(notification)
                notification.config = config
                break

        keys = notification.keys()

        if notification.id in self.map:
            self.remove_notification(notification.id)

        with self.lock:
            self.map[notification.id] = keys
            DataManager._recursive_add_notification(
                self.tree, notification, [*keys, notification.id]
            )

    def _recursive_remove_notification(cluster, keys, i=0):
        key = keys[i]
        last_key = i == len(keys) - 1
        has_key = key in cluster.notifications
        if last_key and not has_key:
            # Short-cutted view, descend
            key = list(cluster.notifications.keys())[0]
            i -= 1

        stop_case = last_key and has_key
        if stop_case:
            cluster_to_delete = cluster.notifications[key]
            last = cluster_to_delete.last()
            nremoved = len(cluster_to_delete)
        else:
            nremoved, last = DataManager._recursive_remove_notification(
                cluster.notifications[key], keys, i + 1
            )

        if len(cluster.notifications[key]) == 0 or stop_case:
            del cluster.notifications[key]

        cluster._len -= nremoved

        if last is cluster._last:
            cluster._last = None

        return nremoved, last

    def remove_notification(self, id, context=()):
        with self.lock:
            if isinstance(id, int):
                context = self.map.pop(id)
            DataManager._recursive_remove_notification(self.tree, [*context, id], i=0)

    def get_context_by_id(self, id):
        return self.get_context(self.map[id])

    def get_context(self, context=()):
        p = self.tree
        for key in context:
            p = p.notifications[key]

        while len(p.notifications) == 1:
            child = list(p.notifications.values())[0]

            if isinstance(child, Notification):
                break

            p = child

        return p
