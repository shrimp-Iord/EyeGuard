# EyeGuard 3.0 — The Hardening Pass

The light-stack lockdown (Standard user, root daemon, control planes on Dad)
closes EyeGuard against a **casual** user completely. A red-team pass found that
a **determined technical** user can still defeat it — and every one of those
attacks traces to a single root cause.

## Headline finding: the agent isn't hardened-runtime signed

Verified on the real machine:

```
codesign -dv .../python3.12
  → flags=0x20002(adhoc,linker-signed)     # NOT hardened runtime
```

Because the session agent runs on an **ad-hoc-signed** interpreter, and it runs
as *your* user, you can manipulate it from the inside with no admin:

- **`lldb -p $(pgrep -f run_agent.py)`** — attach a debugger to the live agent
  and patch `detector.analyze` to return `SAFE`. The agent keeps heartbeating,
  keeps reporting `screen_ok=true`, keeps passing the self-test's liveness
  checks — it just stops flagging. Silent, total, sustained.
- **`DYLD_INSERT_LIBRARIES=evil.dylib python run_agent.py`** — inject a library
  that hijacks the process. It even passes the socket peer check, because the
  process genuinely *is* the real launcher (matching argv).

Everything built assuming "the user can't manipulate the running agent" —
the socket peer check, "the key can't be read from the agent," the self-test —
rests on this being solved. **It isn't, until the agent is a code-signed,
hardened-runtime binary.**

### The fix — and it's FREE (verified on this machine)

It does **not** require the $99 Apple Developer Program. That fee buys
*notarization*, which is only for distributing an app to OTHER Macs without
Gatekeeper warnings — irrelevant here, since EyeGuard is installed locally, not
downloaded. **Ad-hoc hardened-runtime signing is free and sufficient.**

Verified empirically: a fresh binary signed ad-hoc (`flags=0x2 adhoc`) accepts an
`lldb` attach; the *same* binary re-signed with `--options runtime`
(`flags=0x10002 adhoc,runtime`) denies it — *"Not allowed to attach to process."*
`DYLD_INSERT_LIBRARIES` is likewise ignored once the runtime flag is set.

Recipe:
1. Bundle the agent into a single executable (PyInstaller / py2app) so there's
   one main Mach-O to harden (a bare `python run_agent.py` can't be — the
   signature would just be Python's).
2. `codesign -f --options runtime --entitlements ent.plist --sign - <app>`, where
   `ent.plist` grants `com.apple.security.cs.disable-library-validation`
   (self-assignable — lets Python load onnxruntime/numpy/pyobjc under hardened
   runtime) and, if onnxruntime needs it, `allow-unsigned-executable-memory` /
   `allow-jit` — but **NOT** `get-task-allow` (its absence is what denies the
   debugger).
3. Runs locally with no notarization (a locally-built app has no quarantine
   attribute, so Gatekeeper doesn't block it).
4. The vault daemon then verifies the agent's exact **cdhash** (via `SecCode`),
   not just its argv — now meaningful because it's a real signed binary.

The only cost is packaging effort (getting Python + native deps to launch under
hardened runtime with library validation disabled), not money. This converts
three "raise-the-bar" measures into real ones: the peer check *holds*, the
self-test *can't be fed lies*, and the neuter-in-place attack is gone.

## Second finding: the browser is unmanaged

A Standard user installs Firefox extensions **without admin**. Two defeat EyeGuard:

- A **window-title spoofer** makes the green trail log "Firefox — Google" while
  you're on a porn site — the trail's core promise, lying.
- An **adversarial-overlay** extension (the CLIP + NudeNet models are public, so
  this is a white-box attack) keeps images human-viewable but under the
  detection thresholds.

### The fix

**Free, buildable now (makes the attacks tamper-EVIDENT):**

1. **Monitor installed browser extensions.** The agent (running as you) can read
   the extension directories — `~/Library/Application Support/Firefox/Profiles/*/
   extensions/` and Chrome's `.../Extensions/` — and watch them with FSEvents. A
   new/unknown extension → a flag your partner reviews. It doesn't *prevent* the
   title-spoofer or the overlay extension, but it makes installing one **visible**
   — and its integrity now rests on the agent not being neutered, which the free
   hardened-runtime signing (above) secures.
2. **Prefer Safari or Chrome over Firefox.** Their active-tab URL is readable via
   AppleScript straight from the browser's internals — a content extension can't
   easily spoof it, unlike the window *title* (which is all Firefox exposes, and
   exactly what the spoofer rewrites). Switching the daily browser to a
   URL-readable one makes the green trail's site-logging spoof-resistant; you
   could even restrict to Safari/Chrome outright.
3. **Ensemble detection** (already partial): a single adversarial overlay tuned to
   fool CLIP often won't fool NudeNet, and vice-versa. More diverse detectors
   raise the bar further.

**Airtight (paid tier):** manage the browser via **MDM** — enforce an extension
**allow-list** + a **managed content filter**. On a supervised Mac that's a
profile Dad pushes and you can't remove. This is prevention rather than evidence,
but the free measures above cover most of the gap.

## What 3.0 does NOT need to fix
These are genuine scope limits, not holes — no build closes them:
- **A second device** — EyeGuard watches *this* Mac.
- **Content rendered off-screen** (DRM video pixels, AirPlay streaming) — already
  logged by title / green trail.
- **Non-visual content** (text, audio) — the green trail logs the site.

## Priority order for 3.0
1. **Hardened-runtime code-signing** — closes the neuter-in-place attack (the
   single most important remaining fix).
2. **MDM-managed browser** — closes the extension attacks.
3. **Full MDM device management** (`LOCKDOWN.md` §MDM path) — closes the "get
   admin once and it's permanent" residual and gives Recovery Lock + wipe
   survival.

Until then, the honest posture is: **casual users are fully contained; a
determined technical user can neuter the agent in place, and the fix is #1.**
