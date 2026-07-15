# EyeGuard 2.0 — Light-Stack Lockdown (deploy runbook)

Turns the current single-process agent into the **split build**: a root **vault
daemon** (holds the key, does all network) + a **session agent** (captures +
detects, no key, root-owned code). Combined with a Standard account whose admin
password only Dad holds, this closes code-editing and key-reading without MDM.

> Run this **with Dad present** (several steps need admin). Do the account steps
> first — the file moves are pointless until you're a Standard user.

**Layout after lockdown**
| Path | Owner | Holds |
|------|-------|-------|
| `/Library/Application Support/EyeGuard` | **root** (you can read, not write) | code, `config.yaml`, `.supabase_secret` (600), daemon queue |
| `/Library/LaunchDaemons/com.eyeguard.vault.plist` | root | the vault daemon (runs as root) |
| `/Library/LaunchAgents/com.eyeguard.monitor.plist` | root | the session agent (runs as you) |
| `~/Library/Application Support/EyeGuard-data` | you | `flags.jsonl` + frames (tamper-detected; cloud is authoritative) |

---

## A. Accounts & firmware (Dad — do first)

1. **Make a new Admin account for Dad**, with a password you never see.
2. **Demote your daily account to Standard** (System Settings → Users & Groups).
3. **Turn on FileVault** (System Settings → Privacy & Security). When it asks who
   can unlock, ensure **Dad's admin** is enabled — this makes Dad the volume owner.
4. **Verify you are NOT a volume owner** (this is what keeps Recovery closed to you):
   ```
   diskutil apfs listUsers /   # your account should NOT show "Volume Owner: Yes"
   ```
5. **Disable the Guest account** and **fast-user-switching to any unmanaged account.**

## B. Move EyeGuard into root-owned space (Dad / sudo)

Run from the current install directory (`~/Library/Application Support/EyeGuard`):

```bash
SRC="$HOME/Library/Application Support/EyeGuard"
CODE="/Library/Application Support/EyeGuard"
sudo mkdir -p "$CODE/logs"

# copy code only (not data/venv/git)
sudo rsync -a --exclude .venv --exclude .git --exclude logs \
  --exclude flagged_frames --exclude 'flags.jsonl' --exclude 'pending_uploads*' \
  "$SRC"/ "$CODE"/

# key -> root-only; code -> readable but NOT user-writable
sudo install -m 600 -o root -g wheel "$SRC/.supabase_secret" "$CODE/.supabase_secret"
sudo chown -R root:wheel "$CODE"
sudo find "$CODE" -type d -exec chmod 755 {} \;
sudo find "$CODE" -type f -exec chmod 644 {} \;
sudo chmod 600 "$CODE/.supabase_secret"
```

## C. Point config at split mode + the right paths (Dad / sudo)

```bash
DATA="$HOME/Library/Application Support/EyeGuard-data"
mkdir -p "$DATA/flagged_frames"
CONF="/Library/Application Support/EyeGuard/config.yaml"
sudo /usr/bin/sed -i '' \
  -e 's|^  mode: .*|  mode: split|' \
  -e "s|^  flag_log: .*|  flag_log: $DATA/flags.jsonl|" \
  -e "s|^  flagged_frames_dir: .*|  flagged_frames_dir: $DATA/flagged_frames|" \
  -e 's|^  secret_file: .*|  secret_file: /Library/Application Support/EyeGuard/.supabase_secret|' \
  -e 's|^  pending_file: .*|  pending_file: /Library/Application Support/EyeGuard/pending_uploads.jsonl|' \
  -e 's|^  socket_path: .*|  socket_path: /var/run/eyeguard.sock|' \
  "$CONF"
```
(`flag_log` / `flagged_frames_dir` live under `logging:`, the rest under `supabase:` — sed matches by key, so order doesn't matter.)

## D. Install the vault daemon + session agent (Dad / sudo)

```bash
CODE="/Library/Application Support/EyeGuard"
# vault daemon (root)
sudo install -m 644 -o root -g wheel "$CODE/deploy/com.eyeguard.vault.plist" \
  /Library/LaunchDaemons/com.eyeguard.vault.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.eyeguard.vault.plist

# retire the old per-user agent, install the managed one (root-owned, runs as you)
launchctl bootout "gui/$(id -u)/com.eyeguard.monitor" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.eyeguard.monitor.plist"
sudo install -m 644 -o root -g wheel "$CODE/deploy/com.eyeguard.monitor.plist" \
  /Library/LaunchAgents/com.eyeguard.monitor.plist
launchctl bootstrap "gui/$(id -u)" /Library/LaunchAgents/com.eyeguard.monitor.plist
```

> The managed agent (`deploy/com.eyeguard.monitor.plist`) launches
> `python /Library/Application Support/EyeGuard/run_agent.py` — an exact 2-arg
> invocation the vault daemon's peer check pins to. **Test whether you can unload
> it as a Standard user** (`launchctl bootout gui/$(id -u)/com.eyeguard.monitor`)
> — if the OS refuses, capture can't even be stopped; if it allows it, KeepAlive
> relaunches it and the daemon fires a blind alert. Either way it's covered.

## E. Verify (as your Standard account)

Each of these must **fail**:
```bash
cat "/Library/Application Support/EyeGuard/.supabase_secret"   # -> Permission denied
touch "/Library/Application Support/EyeGuard/eyeguard/x"       # -> Permission denied
sudo -v                                                        # -> not in sudoers / needs Dad
launchctl bootout system/com.eyeguard.vault                    # -> Operation not permitted
```
And the dashboard should still show live flags + heartbeat (the daemon is
uploading). Kill the session agent → within ~90s you should get a **blind
alert**; the daemon keeps the record intact.
