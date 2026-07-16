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

### The fix

1. **Enroll in the Apple Developer Program** ($99/yr) → get a **Developer ID
   Application** certificate.
2. **Ship EyeGuard as a signed, hardened-runtime app** (not a bare Python
   interpreter running a script):
   - Bundle the agent with PyInstaller (or py2app) into a single executable.
   - Sign with `codesign --options runtime --sign "Developer ID Application: …"`.
   - Notarize it (`notarytool`).
   - Hardened runtime **without** the `get-task-allow` entitlement makes the
     process **un-debuggable and injection-proof** — `lldb` attach and
     `DYLD_INSERT_LIBRARIES` both fail, even for the owning user.
3. The vault daemon should verify the session agent's **code signature** (Team
   ID / cdhash via `SecCode`), not just its argv — now meaningful because the
   agent is a signed binary, not an interpreter+script (whose signature is just
   Python's).

This converts three "raise-the-bar" measures into real ones: the peer check
*holds*, the self-test *can't be fed lies*, and the neuter-in-place attack is
gone.

## Second finding: the browser is unmanaged

A Standard user installs Firefox extensions **without admin**. Two defeat EyeGuard:

- A **window-title spoofer** makes the green trail log "Firefox — Google" while
  you're on a porn site — the trail's core promise, lying.
- An **adversarial-overlay** extension (the CLIP + NudeNet models are public, so
  this is a white-box attack) keeps images human-viewable but under the
  detection thresholds.

### The fix

Manage the browser via **MDM** (the same Apple Business Manager tier from
`LOCKDOWN.md`'s optional path): enforce an **extension allow-list** and a
**managed content filter**. On a supervised Mac this is a profile Dad pushes and
you can't remove.

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
