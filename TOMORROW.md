# EyeGuard 2.0 — Deploy Day Checklist

Everything to do tomorrow, in order. Full detail for each step lives in the
linked doc — this file is just the ordered punch list so nothing gets missed.
Budget a few hours; do it **with Dad present**, since most steps need his
admin or his logins.

---

## 0. Before touching anything
- [ ] **Full Time Machine backup.** Step 3 wipes the disk.
- [ ] Confirm the Mac is Apple Silicon (it is — M3).
- [ ] Push all pending commits: `cd ~/Library/Application\ Support/EyeGuard && git push`

## 1. Cloud hardening (do first — no wipe needed, safe to do anytime today)
`supabase/harden_pause.sql` — closes the confirmed pause-password brute-force hole.
- [ ] Run it in the Supabase SQL Editor.
- [ ] Set a **long, random** pause password with `./set-pause-password.sh`
      (Dad runs it, you never see the output) and paste the resulting
      `update settings ...` line into the SQL Editor.

## 2. Hand the backend to Dad
Full detail: **`deploy/CONTROL_PLANES.md`**
- [ ] Transfer the Supabase project to Dad's org; rotate the secret key.
- [ ] Dad takes over Resend (new API key, stored in Vault).
- [ ] Transfer the GitHub repo to Dad; he enables Pages from his copy.
- [ ] Update Supabase Auth redirect URL to Dad's new Pages URL.
- [ ] Add `.github/CODEOWNERS` (already in the repo) — put Dad's GitHub
      username in it once the repo is his.
- [ ] Set up branch protection on `main` (see `deploy/WORKFLOW.md` §"One-time
      setup") so nothing merges without Dad's approval.
- [ ] Verify: you can't sign in to Supabase, Resend, or push to the new repo.

## 3. Mac accounts & firmware
Full detail: **`deploy/LOCKDOWN.md`** §A
- [ ] New Admin account for Dad, password only he knows.
- [ ] Demote your account to Standard.
- [ ] Turn on FileVault with **Dad's admin** as the unlock key (makes him
      volume owner).
- [ ] Verify you're **not** a volume owner:
      `diskutil apfs listUsers /` — your account should NOT show
      `Volume Owner: Yes`.
- [ ] Disable Guest account + fast-user-switching to any unmanaged account.

## 4. Move EyeGuard into root-owned space
Full detail: **`deploy/LOCKDOWN.md`** §B–D
- [ ] Copy code to `/Library/Application Support/EyeGuard`, `chown root:wheel`.
- [ ] Move the secret key to the new location, `chmod 600`.
- [ ] Point `config.yaml` at split mode + the new paths (sed block in the doc).
- [ ] Install `com.eyeguard.vault.plist` as a **LaunchDaemon** (root).
- [ ] Retire the old per-user agent; install `com.eyeguard.monitor.plist` as
      the managed **LaunchAgent**.

## 5. Verify every lock
Full detail: **`deploy/LOCKDOWN.md`** §E — each of these must **fail**:
- [ ] `cat ".../EyeGuard/.supabase_secret"` → Permission denied
- [ ] `touch ".../EyeGuard/eyeguard/x"` → Permission denied
- [ ] `sudo -v` (as you) → not in sudoers
- [ ] `launchctl bootout system/com.eyeguard.vault` → Operation not permitted
- [ ] Kill the session agent → **blind alert** fires within ~90s
- [ ] Dashboard still shows live flags + a fresh heartbeat throughout

## 6. Confirm the dev pathway works
Full detail: **`deploy/WORKFLOW.md`**
- [ ] You push a trivial branch + open a PR — merge is blocked without Dad's
      approval.
- [ ] Dad approves + merges a real (or test) change.
- [ ] Dad runs `sudo ./deploy/update.sh` on the Mac and confirms it pulls,
      shows the diff, and restarts both processes.

---

**When all six sections are checked**, EyeGuard is fully locked: you can't
read the key, edit the code, boot another OS, wipe the Mac, touch the cloud
backend, or brute-force the pause password — and you still have a real,
Dad-approved way to keep improving it. Anything that stops monitoring either
can't be done without Dad's password, or trips an alert within 90 seconds.
