"""Reliable Supabase uploader for flags + frame images.

Design goals:
  * Never block the detection loop — uploads run on a background worker thread.
  * Survive offline — each flag is appended to a persistent pending queue; the
    worker retries the whole queue periodically, so a backlog auto-sends the
    moment the network is back (and across restarts).
  * "No alert without an image" — the flag row is only inserted after its image
    uploads; if the local image is gone (e.g. pruned), the flag is dropped.
  * Idempotent — a deterministic row id + upsert means a retry after a crash
    never creates a duplicate.

Only the sb_secret key is used (read from a local file, never in code/config).
It bypasses RLS so the agent can write; the partner dashboard can only read.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_NS = uuid.UUID("e7e9f1c0-0000-4000-8000-eeeeeeeeeeee")  # stable namespace


def _score(reason: str) -> float | None:
    m = re.search(r"clip-(?:red|yellow):([0-9.]+)", reason or "")
    if m:
        return float(m.group(1))
    m = re.search(r"=([0-9.]+)", reason or "")
    return float(m.group(1)) if m else None


class SupabaseUploader:
    def __init__(self, url: str, secret: str, pending_path: str,
                 retry_seconds: int = 60):
        self.base = url.rstrip("/")
        self.secret = secret
        self.pending_path = Path(pending_path)
        self.retry_seconds = retry_seconds
        self._lock = threading.Lock()          # guards the pending file
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- public API ---------------------------------------------------------

    def start(self):
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def enqueue(self, record: dict):
        """Append a flag record to the persistent queue and wake the worker."""
        with self._lock:
            with self.pending_path.open("a") as f:
                f.write(json.dumps(record) + "\n")
        self._wake.set()

    def prune_cloud(self, days: int):
        """Delete frame images older than `days` from the bucket, so the cloud
        wipe matches the local + row retention. Best-effort; never raises.
        (Flag rows themselves are pruned server-side by pg_cron.)"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            old: list[str] = []
            offset = 0
            while True:
                body = json.dumps({
                    "prefix": "", "limit": 100, "offset": offset,
                    "sortBy": {"column": "created_at", "order": "asc"}}).encode()
                req = urllib.request.Request(
                    f"{self.base}/storage/v1/object/list/frames", data=body,
                    method="POST",
                    headers=self._headers({"Content-Type": "application/json"}))
                with urllib.request.urlopen(req, timeout=20) as r:
                    items = json.loads(r.read())
                if not items:
                    break
                for it in items:
                    created, name = it.get("created_at"), it.get("name")
                    if not created or not name:
                        continue
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if dt < cutoff:
                        old.append(name)
                if len(items) < 100:
                    break
                offset += 100
            for i in range(0, len(old), 100):
                req = urllib.request.Request(
                    f"{self.base}/storage/v1/object/frames",
                    data=json.dumps({"prefixes": old[i:i + 100]}).encode(),
                    method="DELETE",
                    headers=self._headers({"Content-Type": "application/json"}))
                with urllib.request.urlopen(req, timeout=30) as r:
                    r.read()
        except Exception:
            pass  # retention must never crash the app

    # ---- worker -------------------------------------------------------------

    def _worker(self):
        while not self._stop.is_set():
            try:
                self._flush()
            except Exception:
                pass  # never let the uploader crash the app
            self._wake.wait(self.retry_seconds)
            self._wake.clear()

    def _flush(self):
        with self._lock:
            if not self.pending_path.exists():
                return
            lines = [l for l in self.pending_path.read_text().splitlines()
                     if l.strip()]
        if not lines:
            return
        remaining: list[str] = []
        for line in lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # drop malformed
            try:
                sent = self._upload(rec)      # True = done (sent or dropped)
            except urllib.error.URLError:
                sent = False                  # offline -> keep for retry
            except Exception:
                sent = False                  # transient server error -> retry
            if not sent:
                remaining.append(line)
        with self._lock:
            tmp = self.pending_path.with_suffix(".tmp")
            tmp.write_text("\n".join(remaining) + ("\n" if remaining else ""))
            tmp.replace(self.pending_path)

    # ---- one record ---------------------------------------------------------

    def _upload(self, rec: dict) -> bool:
        """Upload image then insert the row. Returns True when done (or when the
        image is gone, so we stop retrying a flag we can never complete)."""
        local = rec.get("saved_frame")
        if not local or not Path(local).exists():
            return True  # no image -> no alert; drop from queue
        remote = Path(local).name
        self._put_image(remote, Path(local).read_bytes())   # raises on failure
        self._post_row(self._row(rec, remote))               # raises on failure
        return True

    def _row(self, rec: dict, remote_path: str) -> dict:
        seed = f"{rec.get('timestamp')}|{rec.get('reason')}|{rec.get('display')}"
        return {
            "id": str(uuid.uuid5(_NS, seed)),   # deterministic -> idempotent
            "flagged_at": rec.get("timestamp"),
            "verdict": rec.get("verdict"),
            "is_nudity": bool((rec.get("reason") or "").startswith("nudenet")),
            "grade": rec.get("grade"),
            "risk": rec.get("risk"),
            "app": rec.get("app"),
            "url": rec.get("url"),
            "window_title": rec.get("window_title"),
            "reason": rec.get("reason"),
            "score": _score(rec.get("reason", "")),
            "image_path": remote_path,
        }

    # ---- HTTP (urllib, no extra deps) ---------------------------------------

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"apikey": self.secret, "Authorization": f"Bearer {self.secret}"}
        if extra:
            h.update(extra)
        return h

    def _put_image(self, remote_path: str, data: bytes):
        url = f"{self.base}/storage/v1/object/frames/{remote_path}"
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers=self._headers({"Content-Type": "image/jpeg",
                                   "x-upsert": "true"}))
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()

    def _post_row(self, row: dict):
        url = f"{self.base}/rest/v1/flags"
        req = urllib.request.Request(
            url, data=json.dumps(row).encode(), method="POST",
            headers=self._headers({
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal"}))
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
