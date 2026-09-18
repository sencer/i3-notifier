import json
import os
import socket
import sys

from .rofi_ipc import get_socket_path


def main():
  try:
    try:
      retv = int(os.environ.get("ROFI_RETV", "0"))
    except ValueError:
      retv = 0

    info = os.environ.get("ROFI_INFO", "")
    entry = sys.argv[1] if len(sys.argv) > 1 else ""

    sock_path = get_socket_path()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
      s.settimeout(1.0)
      s.connect(sock_path)

      req = {"retv": retv, "info": info, "entry": entry}
      s.sendall(json.dumps(req).encode("utf-8") + b"\n")

      buf = b""
      while b"\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
          break
        buf += chunk
    finally:
      s.close()

    if not buf:
      sys.exit(0)

    resp = json.loads(buf.decode("utf-8"))
    action = resp.get("action")
    if action != "render":
      sys.exit(0)

    out = sys.stdout
    out.write("\x00use-hot-keys\x1ftrue\n")
    out.write("\x00markup-rows\x1ftrue\n")
    out.write("\x00no-custom\x1ftrue\n")
    out.write("\x00delim\x1f\x01\n")

    if resp.get("keep_selection"):
      out.write("\x00keep-selection\x1ftrue\n")
    if resp.get("prompt"):
      out.write(f"\x00prompt\x1f{resp['prompt']}\n")
    if resp.get("urgent"):
      out.write(f"\x00urgent\x1f{','.join(map(str, resp['urgent']))}\n")
    if resp.get("active"):
      out.write(f"\x00active\x1f{','.join(map(str, resp['active']))}\n")

    entries = resp.get("entries", [])
    if entries:
      out.write("\x01".join(entries) + "\x01")
    out.flush()
  except Exception:
    sys.exit(0)


if __name__ == "__main__":
  main()
