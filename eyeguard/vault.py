"""EyeGuard vault daemon — the privileged half of the split (light-stack) build.

Runs as root (a LaunchDaemon). Holds the Supabase secret key and performs ALL
network writes: flag + image upload, heartbeat, tamper reports, clean beacons.
The unprivileged *session agent* captures the screen and runs detection, then
sends results here over a local unix socket. So:

  * the key never lives in a process the monitored user runs;
  * the agent's code can be root-owned (run-but-not-edit);
  * killing just the capture agent is caught — the daemon reports screen_ok=false
    (blind alert) when the agent goes silent, and the heartbeat stops entirely
    (gone-dark) only if the daemon dies too.

Protocol: newline-delimited JSON over the socket. Ops: flag / status / tamper /
suspend / resume.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path

from .uploader import SupabaseUploader

_BASE = Path(__file__).resolve().parent.parent


class VaultDaemon:
    def __init__(self, uploader: SupabaseUploader, socket_path: str,
                 agent_timeout: int = 90):
        self.uploader = uploader
        self.socket_path = socket_path
        self.agent_timeout = agent_timeout
        self._last_agent = 0.0
        self._last_status = {"screen_ok": True, "frames_analyzed": 0}
        self._lock = threading.Lock()
        # The daemon's heartbeat carries the agent's last-known screen health,
        # but only while the agent is fresh — a silent agent reads as blind.
        uploader.set_status_provider(self._status)

    def _status(self) -> dict:
        with self._lock:
            fresh = (time.time() - self._last_agent) < self.agent_timeout
            st = dict(self._last_status)
        if not fresh:
            st["screen_ok"] = False  # capture agent went silent -> blind
        return st

    def _handle(self, msg: dict):
        op = msg.get("op")
        if op == "flag":
            rec = msg.get("record")
            if isinstance(rec, dict):
                self.uploader.enqueue(rec)
        elif op == "tamper":
            self.uploader.report_tamper(str(msg.get("detail", "unknown")))
        elif op == "suspend":
            self.uploader.suspend()
        elif op == "resume":
            self.uploader.resume()
        elif op == "status":
            s = msg.get("status") or {}
            with self._lock:
                self._last_agent = time.time()
                if "screen_ok" in s:
                    self._last_status["screen_ok"] = bool(s["screen_ok"])
                if "frames_analyzed" in s:
                    self._last_status["frames_analyzed"] = int(s["frames_analyzed"])

    def serve(self):
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.socket_path)
        # The session agent (a different, unprivileged user) must be able to
        # connect. It can only ADD detections — never delete or forge a beacon —
        # so an open socket is safe (worst case is self-incriminating noise).
        os.chmod(self.socket_path, 0o666)
        srv.listen(16)
        self.uploader.start()  # heartbeat + upload worker
        print(f"[vault] listening on {self.socket_path}", flush=True)
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                continue
            threading.Thread(target=self._client, args=(conn,),
                             daemon=True).start()

    def _client(self, conn: socket.socket):
        buf = b""
        try:
            while True:
                data = conn.recv(8192)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line.strip():
                        try:
                            self._handle(json.loads(line))
                        except Exception:
                            pass  # never let one bad message kill the daemon
        finally:
            conn.close()


def build_uploader_from_config(cfg: dict) -> SupabaseUploader:
    sb = cfg.get("supabase", {})
    secret_path = Path(sb.get("secret_file", ".supabase_secret"))
    if not secret_path.is_absolute():
        secret_path = _BASE / secret_path
    secret = secret_path.read_text().strip()
    pending = Path(sb.get("pending_file", "pending_uploads.jsonl"))
    if not pending.is_absolute():
        pending = _BASE / pending
    return SupabaseUploader(url=sb["url"], secret=secret,
                            pending_path=str(pending),
                            retry_seconds=int(sb.get("retry_seconds", 60)),
                            heartbeat=bool(sb.get("heartbeat", True)))


def main():
    import argparse
    from .main import load_config
    p = argparse.ArgumentParser(prog="eyeguard-vault")
    p.add_argument("--config", default=str(_BASE / "config.yaml"))
    args = p.parse_args()
    cfg = load_config(args.config)
    sb = cfg.get("supabase", {})
    sock = sb.get("socket_path", "/var/run/eyeguard.sock")
    uploader = build_uploader_from_config(cfg)
    VaultDaemon(uploader, sock,
                agent_timeout=int(sb.get("agent_timeout", 90))).serve()


if __name__ == "__main__":
    main()
