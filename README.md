# EyeGuard

A 24/7 screen-content accountability monitor for macOS, with a private cloud
layer that gives an accountability partner full visibility.

Unlike text/URL-based accountability tools, EyeGuard analyzes the **actual screen
pixels** — so it sees content regardless of which app, browser, video, game, or
window it appears in. Detection runs **entirely on-device**; only flags and small
review images are synced to the partner's dashboard.

---

## What it does

- **Watches the screen 24/7** — samples the framebuffer every few seconds, skips
  near-identical frames, and analyzes what's actually on screen.
- **Flags revealing / explicit content** with two tiers — 🔴 *Revealing* (nude or
  very revealing) and 🟡 *Suggestive* (swimwear / gym / borderline).
- **Logs a full browsing trail** — a 🟢 *Browsing* record (app + site + time, no
  image) on every context change, so a reviewer sees **everywhere** you went, not
  just the frames that tripped the detector. Nothing hides in a gap.
- **Notifies the partner** by email — 🔴 red = instant, ⚫ gone-dark = if the Mac
  goes silent unexpectedly, 🟡 suggestive = a daily digest.
- **Partner dashboard** — a private web app (live feed, history, filters, blurred
  review images) that only the partner can log into.
- **Tamper-evident** — a heartbeat means any secret shutdown, disable, or going
  offline surfaces as a "monitoring went dark" alert.
- **Self-cleaning** — all data auto-deletes after 7 days, locally and in the cloud.

## Architecture

```
        ┌──────────────────────── your Mac ────────────────────────┐
        │  screen capture (mss) → frame-change filter               │
        │        │                                                  │
        │  NudeNet (fast NSFW)  +  CLIP zero-shot (head-to-head)     │  onnxruntime,
        │        │                                                  │  no PyTorch
        │  context-risk grading (app / site / window → keep + grade)│
        │        │                                                  │
        │  local log + live HTML report        menu-bar app (status)│
        │        │                                                  │
        │  uploader (offline queue, blurred reds)   heartbeat pulse │
        └────────┼──────────────────────────────────┼──────────────┘
                 ▼                                   ▼
        ┌──────────────────────── Supabase ─────────────────────────┐
        │  Postgres (flags, device_status)   private image bucket    │
        │  row-level security → partner-only  pg_cron 7-day wipe      │
        │  pg_net → Resend  ── red / gone-dark / digest emails ──▶ 📧 │
        └────────────────────────────┬───────────────────────────────┘
                                     ▼
                    partner dashboard (static app on GitHub Pages)
                    magic-link login · live feed · read-only
```

## Detection

- **NudeNet** (trained nudity detector) runs first as a fast explicit-content pass.
- **CLIP zero-shot** runs on every frame and scores it **head-to-head**: the best
  explicit prompt vs. the best suggestive prompt vs. the best *safe* prompt,
  softmaxed against each other. Strong "safe anchor" prompts (clothed people,
  animals, gameplay, text posts, UI, art) give neutral content a home so it isn't
  forced onto a body/nudity hub — this is what keeps false positives low.
- Small on-screen windows are caught by tiling the frame into an overlapping grid;
  tiles must clear a higher bar than the full frame since they're noisier.
- A **context-risk layer** (no AI, just rules) combines the CLIP score with *where*
  it happened. Safe contexts (terminal, code editors, this tool's own report) are
  suppressed; risky contexts (social media) are surfaced and graded up. This keeps
  detection sensitive without flooding on safe screens.

Runs on **onnxruntime** (CLIP encoders exported to ONNX, verified identical to the
PyTorch originals) — no PyTorch, tuned to fit an 8 GB Mac.

## Cloud & partner layer

- **Supabase** — Postgres + Storage + Auth. The agent writes with a server-side
  secret key; the partner dashboard can only **read**, and only the two
  pre-registered accounts can log in (magic-link, public signups off). No one can
  edit or delete the record from the dashboard side.
- **Dashboard** (`docs/`) — a self-contained static page hosted on GitHub Pages.
- **Email** — server-side `pg_cron` + `pg_net` → Resend, from a dedicated sending
  subdomain (isolated from any existing email on the domain).
- **Retention** — `pg_cron` wipes flag rows after 7 days; the agent wipes the cloud
  images and its local copies on the same schedule.

## Repo layout

| Path | What |
|------|------|
| `eyeguard/` | the agent — capture, detector, risk, logger, uploader, menubar, context, retention, viewer |
| `models/` | ONNX CLIP encoders + NudeNet (not committed) |
| `docs/index.html` | the partner dashboard (GitHub Pages) |
| `supabase/*.sql` | database schema, RLS lock, heartbeat, and alert jobs (run once in the SQL Editor) |
| `config.yaml` | all thresholds, prompts, context rules, retention, cloud settings |
| `*.sh` | setup / build / install scripts |

## Setup (local agent)

Requires Python 3.12 (not all ML wheels support newer yet).

```bash
./setup.sh            # create .venv, install deps, fetch models
./install_agent.sh    # run now + at every login, as a menu-bar app
```

Grant **Screen Recording** on first launch (System Settings → Privacy & Security →
Screen Recording). The menu-bar eye shows status: 🟢 watching · 🟡 recent
suggestive · 🔴 recent revealing · ⚠️ not watching. It relaunches if killed and has
no quit button (stop it with `./uninstall_agent.sh`).

The cloud layer (Supabase project, Resend key, dashboard hosting, partner accounts)
is configured separately — see the `supabase/` scripts and `config.yaml`.

## Privacy & security

- **Detection is 100% local** — frames are analyzed in memory. Only flags and small
  review images (reds are **blurred**) sync to the partner.
- **Partner data is locked down** — row-level security restricts reads to the two
  partner accounts; the dashboard is read-only; the agent's key is server-side only.
- **Everything auto-deletes after 7 days**, on the Mac and in the cloud.

## Status

- ✅ **Detection core** — capture, tiered NudeNet + CLIP, context-risk grading.
- ✅ **Always-on** — menu-bar app + login agent, self-relaunching.
- ✅ **Partner layer** — cloud sync, browsing trail, dashboard, email alerts.
- ✅ **Tamper-evidence** — heartbeat + gone-dark alerts (sleep/shutdown-aware).
- ⬜ **Config lock (Phase 4)** — partner-held credential to gate stopping /
  uninstalling the agent, plus log-tamper detection.
