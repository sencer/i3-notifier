import json
import logging
import os
import tempfile
import threading
import time

from .notification import Notification, NotificationCluster

logger = logging.getLogger(__name__)


class DataManager:
  __slots__ = "tree", "map", "lock", "configs", "dump_path", "last", "_loading"

  def __init__(self, configs, dump_path):

    self.tree = NotificationCluster()
    self.map = dict()
    self.last = None

    self.lock = threading.RLock()
    self.configs = configs
    self.dump_path = dump_path
    self._loading = True

    try:
      if dump_path and dump_path not in ("/dev/null", os.devnull) and os.path.exists(dump_path):
        with open(dump_path, "r") as f:
          now = time.time_ns()
          for d in json.load(f):
            notification = Notification(**d)
            for config in self.configs:
              if config.should_apply(notification):
                config.update_notification(notification)
                notification.config = config
                break

            if notification.expires and notification.expires_at is not None:
              if notification.expires_at <= now:
                continue

            keys = notification.keys()
            self.map[notification.id] = keys
            DataManager._recursive_add_notification(
              self.tree, notification, [*keys, notification.id]
            )
            self.last = notification
    except FileNotFoundError:
      logger.info("No dump file found, starting fresh.")
    except json.JSONDecodeError:
      logger.info("Dump file was empty or invalid, starting fresh.")
    except Exception as e:
      logger.error(f"Failed to load dump file: {e}")
    finally:
      self._loading = False

  def _recursive_add_notification(cluster, notification, keys, i=0):
    if i == len(keys):
      return

    if keys[i] not in cluster.notifications:
      cluster.notifications[keys[i]] = NotificationCluster()

    DataManager._recursive_add_notification(
      cluster.notifications[keys[i]], notification, keys, i + 1
    )
    cluster.add(keys[i], notification)

  def add_notification(self, notification, dump=True):
    for config in self.configs:
      if config.should_apply(notification):
        config.update_notification(notification)
        notification.config = config
        break

    if notification.expires and notification.expires_at is not None:
      if notification.expires_at <= time.time_ns():
        return

    keys = notification.keys()

    if notification.id in self.map:
      self.remove_notification(notification.id, dump=False)

    with self.lock:
      self.last = notification
      self.map[notification.id] = keys
      DataManager._recursive_add_notification(
        self.tree, notification, [*keys, notification.id]
      )

    if dump and not self._loading:
      self.dump(force_sync=False)

  def _recursive_remove_notification(cluster, keys, i=0):
    key = keys[i]
    best_key = i == len(keys) - 1
    has_key = key in cluster.notifications
    if best_key and not has_key:
      # Short-cutted view, descend
      key = list(cluster.notifications.keys())[0]
      i -= 1

    stop_case = best_key and has_key
    if stop_case:
      cluster_to_delete = cluster.notifications[key]
      best = cluster_to_delete.best
      urgency = cluster.urgency
      nremoved = len(cluster_to_delete)
    else:
      nremoved, best, urgency = DataManager._recursive_remove_notification(
        cluster.notifications[key], keys, i + 1
      )

    if len(cluster.notifications[key]) == 0 or stop_case:
      del cluster.notifications[key]

    cluster._len -= nremoved

    if best is cluster._best:
      cluster._best = None

    if urgency == cluster._urgency:
      cluster._urgency = None

    return nremoved, best, urgency

  def remove_notification(self, id, context=(), dump=True):
    removed = False
    with self.lock:
      if isinstance(id, int):
        if self.last and id == self.last.id:
          self.last = None

        context = self.map.pop(id, None)
        if context is not None:
          removed = True
          ctx = self.get_context(context)
          if id in ctx.notifications:
            notification = ctx.notifications[id]
            if notification.timer is not None:
              notification.timer.cancel()
          DataManager._recursive_remove_notification(self.tree, [*context, id], i=0)
      else:
        ctx = self.get_context(context)
        if id in ctx.notifications:
          removed = True
          for leaf in ctx.notifications[id].leafs():
            if self.last and leaf.id == self.last.id:
              self.last = None
            if leaf.timer is not None:
              leaf.timer.cancel()
            self.map.pop(leaf.id, None)

          DataManager._recursive_remove_notification(self.tree, [*context, id], i=0)

    if removed and dump and not self._loading:
      self.dump(force_sync=False)

    return removed

  def get_context_by_id(self, id):
    return self.get_context(self.map[id])

  def get_context(self, context=(), auto_descend=True):
    p = self.tree

    if context and context[0] not in p.notifications:
      while len(p.notifications) == 1:
        p = next(iter(p.notifications.values()))

    for key in context:
      p = p.notifications[key]

    while auto_descend and len(p.notifications) == 1:
      child = next(iter(p.notifications.values()))

      if isinstance(child, Notification):
        break

      if len(child) > 1 and p is self.tree and not context:
        break

      p = child

    return p

  def dump(self, force_sync=True, fsync=False):
    if not self.dump_path or self.dump_path in ("/dev/null", os.devnull):
      return

    with self.lock:
      data = [notification.to_dict() for notification in self.tree.leafs()]

    tmp_path = None
    try:
      dump_dir = os.path.dirname(os.path.abspath(self.dump_path))
      os.makedirs(dump_dir, exist_ok=True)

      with tempfile.NamedTemporaryFile(
        mode="w",
        dir=dump_dir,
        prefix=".dump_",
        suffix=".tmp",
        delete=False,
      ) as f:
        tmp_path = f.name
        json.dump(data, f, indent=4)
        f.flush()
        if fsync:
          os.fsync(f.fileno())

      os.replace(tmp_path, self.dump_path)
    except Exception as e:
      logger.error(f"Failed to dump notifications: {e}")
      if tmp_path and os.path.exists(tmp_path):
        try:
          os.remove(tmp_path)
        except OSError:
          pass

  def cancel_timers(self):
    with self.lock:
      leafs = list(self.tree.leafs())
    for notification in leafs:
      if notification.timer is not None:
        notification.timer.cancel()
