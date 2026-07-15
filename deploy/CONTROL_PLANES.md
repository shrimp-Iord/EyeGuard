# EyeGuard 2.0 — Hand the Control Planes to Dad

The Mac lockdown (`LOCKDOWN.md`) stops you tampering with the *device*. This stops
you tampering with the *backend*. Right now **you own the Supabase project, the
Resend account, and the GitHub repo/dashboard** — each is a console you could log
into and undo everything (disable append-only, delete flags, silence emails, or
doctor the dashboard your partners read). For real accountability, the person
being monitored must not administer the system.

**Principle:** Dad holds every admin login. Your agent keeps only a write key it
can't misuse (append-only), stored where you can't read it (the root vault daemon).

Do these once, ideally the same day as the Mac lockdown.

---

## 1. Supabase — Dad owns the project

**Option A (cleanest): transfer the existing project.**
1. Dad creates a free Supabase account + organization.
2. You: Supabase → the project → **Settings → General → Transfer project** → to
   Dad's organization. Then remove yourself as an org member.
3. Dad: **Settings → API → rotate the `service_role` / secret key.** This voids
   any copy you kept. Put the new secret only into the root-owned
   `/Library/Application Support/EyeGuard/.supabase_secret` (during the Mac
   lockdown, so it's root-600 — you never see it).

**Option B (if transfer is fussy): Dad recreates it.**
Dad makes the project, runs every `supabase/*.sql` file, creates the two partner
logins, and hands you only the new URL + publishable key for the dashboard and the
new secret for the daemon.

**Verify:** you can no longer sign in to supabase.com for this project.

## 2. Resend — Dad owns the sender

Resend doesn't transfer cleanly, so simplest is Dad takes it over:
1. Dad creates a Resend account (or you change the existing account's email +
   password to Dad's and hand it off).
2. Re-verify the sending domain under Dad's account, **create a fresh API key**,
   and store it in Supabase Vault (`select vault.create_secret('re_...','resend_api_key')`).
   Delete the old key.

**Verify:** you can't sign in to Resend; alerts still arrive.

## 3. GitHub + dashboard — Dad hosts what partners read

The dashboard is code your partners load, so it must not be code you control.
1. **Transfer the repo:** GitHub → repo **Settings → Transfer ownership** → to
   Dad's account. (Or Dad forks it.) Dad enables **Pages** from *his* `main`/`docs`.
2. The partner dashboard URL becomes Dad's, e.g.
   `https://<dad-username>.github.io/EyeGuard/`.
3. In Supabase → **Authentication → URL Configuration**, set Site URL + redirect
   to Dad's Pages URL. Update `docs/index.html` only through Dad's repo.

**Verify:** you have no write access to the repo serving the dashboard.

## 4. Lock the pause check (do now, before/independent of the above)

Run `supabase/harden_pause.sql` in the SQL Editor. It stops the public key from
brute-forcing the pause password and adds a 5-try / 15-min lockout. Also make the
pause password **long and random** — Dad generates it with `set-pause-password.sh`
and you never see it.

---

## Why this matters (the through-line)

Every serious weakness left in EyeGuard reduces to *you being both the monitored
user and the administrator*. The Mac lockdown removes your device admin; this
removes your backend admin. After both:

- You can't read or change the agent's key (root daemon).
- You can't edit the code, boot another OS, or wipe the Mac (Dad's admin).
- You can't disable append-only, delete flags, silence emails, or doctor the
  dashboard (Dad's Supabase / Resend / GitHub).
- Anything that stops the agent still trips the gone-dark / blind alert.

What remains is genuinely out of scope for a screen monitor (a second device,
content rendered off-screen) — not a hole in the system.
