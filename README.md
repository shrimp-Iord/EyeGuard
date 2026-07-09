# EyeGuard

A **local-only**, 24/7 screen-content accountability monitor for macOS.

Unlike text/URL-based accountability tools, EyeGuard analyzes the **actual screen
pixels** — so it sees content regardless of which app, browser, video, game, or
emulated environment it appears in. All analysis runs **on-device**; no screen
data ever leaves the machine.

## Status: Phase 1 — Detection Core

This phase proves the detection pipeline works and lets you tune its sensitivity
before any always-on / notification / tamper-resistance layers are built.

### Pipeline

```
Screen capture (every N seconds)
      │
 Frame-change filter   ← skip near-identical frames (saves most of the work)
      │
 Fast NSFW classifier  ← always-on first pass (NudeNet, runs in ms on CPU)
      │  (ambiguous score?)
 Small vision model    ← arbitrates borderline frames only (Moondream, optional)
      │  (flagged)
 Flag logger           ← appends to a local JSONL log
```

The fast classifier is tuned **permissive** (flags generously). The optional
small vision model arbitrates the borderline band so you aren't drowned in false
positives. Nothing is sent anywhere in Phase 1 — flags are written to a local log
you can review.

## Roadmap

- **Phase 1 — Detection core** (this) — capture + tiered detection + local log.
- **Phase 2 — Notifier** — email the accountability partner on a flag (flag only, no image).
- **Phase 3 — Tamper-evidence** — LaunchDaemon (runs at boot/all users), watchdog
  process, "monitoring went dark" alerts on stop / user-switch / permission-revoke.
- **Phase 4 — Config lock** — config + uninstall gated behind a partner-held credential.

## Setup

Requires Python 3.12 (ML wheels don't all support 3.14 yet). From the project root:

```bash
./setup.sh          # creates .venv, installs deps, downloads the classifier model
```

Then grant **Screen Recording** permission the first time you run it
(System Settings → Privacy & Security → Screen Recording → enable your terminal).

## Run

### In a terminal (for tuning)

```bash
./run.sh                       # uses config.yaml defaults
./run.sh --interval 3          # capture every 3 seconds
./run.sh --once                # analyze a single frame and exit (good for testing)
```

Flags are written to `flags.jsonl` in the project root. Tail it to watch:

```bash
tail -f flags.jsonl
```

### As a menu bar app (no terminal)

```bash
./install_agent.sh             # starts now + at every login; shows a menu bar icon
./uninstall_agent.sh           # stop and remove it
```

A 🟢 icon appears in the menu bar (🟡 = recent suggestive, 🔴 = recent explicit,
⚠️ = not watching). The menu shows flag counts, the last flag (with the app/site
it came from), and an "Open flag log" item. It relaunches automatically if killed.

### Flag corroboration (what app/site was active)

Every flag is stamped — locally, with no external service — with the frontmost
**app**, the active **URL** (Safari/Chrome/Brave/Edge/Arc; Firefox doesn't expose
URLs to automation, so it gets the **window title** instead), and the front
**window title**. Granting Accessibility + Automation permission on first launch
enables the URL/title fields; without them you still get the app name.

## Privacy

- All inference is local. No network calls in Phase 1.
- Captured frames are held in memory only and discarded after analysis — they are
  **not** written to disk unless you enable `save_flagged_frames` in `config.yaml`
  (off by default; intended only for tuning).
- **Data retention:** flag data (the JSONL log and any saved frames) is kept for
  `logging.retention_days` (default **7**) and then automatically deleted. Pruning
  runs at startup and hourly (menu bar app).
