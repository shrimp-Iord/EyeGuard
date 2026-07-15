"""VaultClient — the session agent's stand-in for the uploader in split mode.

Exposes the same surface the menu-bar app already calls (enqueue, report_tamper,
set_status_provider, suspend, resume, start) but forwards everything to the root
vault daemon over a local unix socket. It holds NO secret key and does no network
itself — the daemon owns the key, the heartbeat, and every write. This is what
lets the agent run as the (root-owned, unprivileged) capture process.
"""

from __future__ import annotations

import json
import socket
import threading
import time


class VaultClient:
    def __init__(self, socket_path: str, status_interval: int = 30):
        self.socket_path = socket_path
        self.status_interval = status_interval
        self._status_provider = None
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()

    # ---- uploader-compatible surface ---------------------------------------

    def set_status_provider(self, fn):
        self._status_provider = fn

    def start(self):
        threading.Thread(target=self._status_loop, daemon=True).start()

    def enqueue(self, record: dict):
        self._send({"op": "flag", "record": record})

    def report_tamper(self, detail: str):
        self._send({"op": "tamper", "detail": detail})

    def suspend(self):
        self._send({"op": "suspend"})

    def resume(self):
        self._send({"op": "resume"})

    # ---- socket plumbing ----------------------------------------------------

    def _connect(self) -> socket.socket:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(self.socket_path)
        return s

    def _send(self, msg: dict):
        line = (json.dumps(msg) + "\n").encode()
        with self._lock:
            for attempt in (1, 2):  # reconnect once if the daemon restarted
                try:
                    if self._sock is None:
                        self._sock = self._connect()
                    self._sock.sendall(line)
                    return
                except OSError:
                    try:
                        if self._sock:
                            self._sock.close()
                    except OSError:
                        pass
                    self._sock = None
            # daemon unreachable: drop this message. The daemon's own heartbeat
            # will go dark on its own if it's truly down -> gone-dark alert.

    def _status_loop(self):
        while not self._stop.is_set():
            if self._status_provider is not None:
                try:
                    self._send({"op": "status", "status": self._status_provider()})
                except Exception:
                    pass
            self._stop.wait(self.status_interval)
