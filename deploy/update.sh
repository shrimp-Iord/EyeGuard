#!/usr/bin/env bash
# Pull the latest approved code into the LOCKED (root-owned) install and restart.
# Run with sudo — Dad types the password. This is the ONLY way code in
# /Library/Application Support/EyeGuard ever changes after the lockdown.
#
# Safety: it only ever moves the deployed copy to origin/main — the branch
# GitHub's branch protection requires Dad's review to merge into (see
# WORKFLOW.md). There is no path from "Jonah's laptop" to this script that
# skips that review.
set -euo pipefail

CODE="/Library/Application Support/EyeGuard"

if [ "$EUID" -ne 0 ]; then
  echo "Run with sudo: sudo ./update.sh" >&2
  exit 1
fi

cd "$CODE"
echo "Current commit: $(git log --oneline -1)"

git fetch origin main
echo
echo "Incoming changes (origin/main vs deployed):"
git log --oneline HEAD..origin/main || true
echo
read -r -p "Deploy these changes? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted — nothing deployed."; exit 0; }

# Hard reset the CODE tree to exactly what's on main. Data (flags, keys,
# pending queue) lives outside this tree (see LOCKDOWN.md layout) so a reset
# here never touches monitoring history.
git reset --hard origin/main

# Re-apply ownership in case the pull added new files.
chown -R root:wheel "$CODE"
find "$CODE" -type d -exec chmod 755 {} \;
find "$CODE" -type f -exec chmod 644 {} \;
chmod 600 "$CODE/.supabase_secret" 2>/dev/null || true

echo "Restarting vault daemon + session agent..."
launchctl kickstart -k system/com.eyeguard.vault
CONSOLE_UID=$(stat -f%u /dev/console)
launchctl kickstart -k "gui/$CONSOLE_UID/com.eyeguard.monitor" 2>/dev/null || true

echo "Deployed $(git log --oneline -1)."
