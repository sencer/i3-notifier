import json
import logging
import os
import socket
from gi.repository import GLib

logger = logging.getLogger(__name__)

DEFAULT_SOCKET_NAME = "rofi.sock"


def get_socket_path():
  override = os.environ.get("I3_NOTIFIER_SOCKET")
  if override:
    return override
  runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
  if runtime_dir:
    sock_dir = os.path.join(runtime_dir, "i3-notifier")
  else:
    sock_dir = f"/tmp/i3-notifier-{os.getuid()}"
  os.makedirs(sock_dir, mode=0o700, exist_ok=True)
  return os.path.join(sock_dir, DEFAULT_SOCKET_NAME)


class RofiIPCServer:
  def __init__(self, request_handler, socket_path=None):
    self.request_handler = request_handler
    self.socket_path = socket_path or get_socket_path()
    self.sock = None
    self.source_id = None
    self._setup_socket()

  def _setup_socket(self):
    if os.path.exists(self.socket_path):
      test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      try:
        test_sock.connect(self.socket_path)
        logger.warning(
          f"Another instance may be listening on {self.socket_path}. Unlinking."
        )
      except (ConnectionRefusedError, FileNotFoundError, OSError):
        pass
      finally:
        test_sock.close()
      try:
        os.unlink(self.socket_path)
      except OSError:
        pass

    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    self.sock.bind(self.socket_path)
    os.chmod(self.socket_path, 0o600)
    self.sock.listen(5)
    self.sock.setblocking(False)

    self.source_id = GLib.io_add_watch(
      self.sock.fileno(),
      GLib.PRIORITY_DEFAULT,
      GLib.IOCondition.IN,
      self._on_connection,
    )
    logger.info(f"Rofi IPC server listening on {self.socket_path}")

  def _on_connection(self, fd, condition):
    try:
      try:
        client, _ = self.sock.accept()
      except (BlockingIOError, InterruptedError):
        return True
      except Exception as e:
        logger.error(f"Rofi IPC accept error: {e}")
        return True

      client.settimeout(1.0)
      buffer = b""
      while b"\n" not in buffer:
        chunk = client.recv(4096)
        if not chunk:
          break
        buffer += chunk
      if buffer:
        req = json.loads(buffer.decode("utf-8"))
        resp = self.request_handler(req)
        client.sendall(json.dumps(resp).encode("utf-8") + b"\n")
      client.close()
    except Exception as e:
      logger.error(f"Rofi IPC communication error: {e}", exc_info=True)
    return True

  def close(self):
    if self.source_id is not None:
      try:
        GLib.source_remove(self.source_id)
      except Exception:
        pass
      self.source_id = None
    if self.sock is not None:
      try:
        self.sock.close()
      except Exception:
        pass
      self.sock = None
    if os.path.exists(self.socket_path):
      try:
        os.unlink(self.socket_path)
      except OSError:
        pass
