"""Data retention: keep flag data for N days, then delete it.

Prunes both the JSONL flag log (dropping entries older than the window) and any
saved flagged frames on disk. Safe to call often — it's cheap and idempotent.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _cutoff(retention_days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=retention_days)


def prune_flag_log(flag_log: str | Path, retention_days: int) -> int:
    """Rewrite the JSONL log keeping only entries newer than the window.
    Returns the number of entries dropped. Malformed lines are dropped."""
    path = Path(flag_log)
    if not path.exists():
        return 0
    cutoff = _cutoff(retention_days)
    kept, dropped = [], 0
    with path.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["timestamp"])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    kept.append(line)
                else:
                    dropped += 1
            except (ValueError, KeyError):
                dropped += 1  # malformed / unparseable -> drop
    if dropped:
        # Atomic replace so a crash mid-write can't corrupt the log.
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(fd, "w") as out:
            for line in kept:
                out.write(line + "\n")
        os.replace(tmp, path)
    return dropped


def prune_frames(frames_dir: str | Path, retention_days: int) -> int:
    """Delete saved flagged-frame images older than the window (by mtime).
    Returns the number of files deleted."""
    d = Path(frames_dir)
    if not d.exists():
        return 0
    cutoff_ts = _cutoff(retention_days).timestamp()
    deleted = 0
    for p in d.iterdir():
        if p.is_file() and p.stat().st_mtime < cutoff_ts:
            try:
                p.unlink()
                deleted += 1
            except OSError:
                pass
    return deleted


def prune(cfg: dict) -> dict:
    """Apply retention per config['logging']. Returns a small summary dict."""
    log_cfg = cfg.get("logging", {})
    days = int(log_cfg.get("retention_days", 7))
    summary = {
        "retention_days": days,
        "log_entries_dropped": prune_flag_log(log_cfg.get("flag_log",
                                                          "flags.jsonl"), days),
        "frames_deleted": prune_frames(
            log_cfg.get("flagged_frames_dir", "flagged_frames"), days),
    }
    return summary
