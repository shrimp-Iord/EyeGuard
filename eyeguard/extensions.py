"""Browser-extension monitoring.

A window-title spoofer can hide the site from the green trail; an image / canvas
/ overlay extension can fool the detector. Both are installable by a Standard
user without admin. This can't PREVENT them, but it makes them tamper-EVIDENT:
the agent baselines installed extensions at startup and flags any NEW one — an
obviously-evasive one (matching the questionable list) as an immediate red alert,
anything else as a yellow "review" flag.

scan() returns {(browser, ext_id): name} across Firefox + Chromium browsers.
"""

from __future__ import annotations

import json
from pathlib import Path

_APPSUP = Path.home() / "Library" / "Application Support"

# Chromium-family browsers: display name -> Application Support subpath.
_CHROMIUM = {
    "Chrome": "Google/Chrome",
    "Chrome Canary": "Google/Chrome Canary",
    "Brave": "BraveSoftware/Brave-Browser",
    "Edge": "Microsoft Edge",
    "Vivaldi": "Vivaldi",
}


def _chrome_name(verdir: Path, raw: str) -> str | None:
    """Resolve a Chrome __MSG_key__ localized name from _locales."""
    if not (raw.startswith("__MSG_") and raw.endswith("__")):
        return raw
    key = raw[6:-2]
    for loc in ("en", "en_US", "en_GB"):
        mp = verdir / "_locales" / loc / "messages.json"
        if mp.exists():
            try:
                d = json.loads(mp.read_text())
                entry = d.get(key) or d.get(key.lower()) or {}
                if entry.get("message"):
                    return entry["message"]
            except Exception:
                pass
    return None


def _firefox(out: dict):
    root = _APPSUP / "Firefox" / "Profiles"
    if not root.exists():
        return
    for prof in root.glob("*"):
        ej = prof / "extensions.json"
        if not ej.exists():
            continue
        try:
            data = json.loads(ej.read_text())
        except Exception:
            continue
        for a in data.get("addons", []):
            if a.get("type") != "extension":
                continue
            if not str(a.get("location", "")).startswith("app-profile"):
                continue  # user-installed only, not built-ins
            eid = a.get("id") or ""
            name = (a.get("defaultLocale") or {}).get("name") or eid
            out[("Firefox", eid)] = name


def _chromium(out: dict):
    for bname, sub in _CHROMIUM.items():
        base = _APPSUP / sub
        if not base.exists():
            continue
        for extsdir in base.glob("*/Extensions"):   # one per profile
            for extdir in extsdir.glob("*"):
                if not extdir.is_dir() or extdir.name in ("Temp", ".DS_Store"):
                    continue
                eid = extdir.name
                name = eid
                for ver in sorted(extdir.glob("*"), reverse=True):
                    mf = ver / "manifest.json"
                    if mf.exists():
                        try:
                            m = json.loads(mf.read_text())
                            name = _chrome_name(ver, m.get("name") or eid) or eid
                        except Exception:
                            name = eid
                        break
                out[(bname, eid)] = name


def scan() -> dict:
    """{(browser, ext_id): name} of user-installed browser extensions."""
    out: dict = {}
    try:
        _firefox(out)
    except Exception:
        pass
    try:
        _chromium(out)
    except Exception:
        pass
    return out


def is_questionable(name: str, patterns: list[str]) -> bool:
    n = (name or "").lower()
    return any(p in n for p in patterns)
