#!/usr/bin/env bash
# Relocate EyeGuard out of ~/Desktop (a TCC-protected folder) to
# ~/Library/Application Support/EyeGuard, so EyeGuard.app can run as the always-on
# agent with its own identity. Copies everything (incl. the venv, which is
# relocatable since we invoke .venv/bin/python directly), rebuilds the app at the
# new path, drops a launchable alias in ~/Applications, and reinstalls the agent.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/Application Support/EyeGuard"
APPS="$HOME/Applications"
LABEL="com.eyeguard.monitor"

echo "==> Stopping current agent"
launchctl unload "$HOME/Library/LaunchAgents/$LABEL.plist" 2>/dev/null || true

echo "==> Copying project to: $DEST"
mkdir -p "$DEST"
# Exclude caches, temp art, logs, and the old bundle (rebuilt fresh at new path).
rsync -a --delete \
  --exclude '__pycache__' \
  --exclude 'assets/_tmp' \
  --exclude 'logs' \
  --exclude 'EyeGuard.app' \
  --exclude 'flags_readable.txt' \
  "$SRC"/ "$DEST"/

echo "==> Verifying the relocated venv works"
"$DEST/.venv/bin/python" -c "import eyeguard, torch, transformers, rumps; print('relocated venv OK')" \
  >/dev/null 2>&1 || { echo "Relocated venv failed to import — aborting." >&2; exit 1; }
echo "    relocated venv OK"

echo "==> Rebuilding EyeGuard.app at the new location"
( cd "$DEST" && ./build_app.sh >/dev/null )

echo "==> Linking into ~/Applications for Launchpad/Finder (optional)"
if mkdir -p "$APPS" 2>/dev/null && [ -w "$APPS" ]; then
  rm -rf "$APPS/EyeGuard.app" 2>/dev/null || true
  ln -s "$DEST/EyeGuard.app" "$APPS/EyeGuard.app" \
    && echo "    linked $APPS/EyeGuard.app" \
    || echo "    (couldn't link into ~/Applications — skipping; not required)"
else
  echo "    ~/Applications not writable — skipping alias (not required)."
  echo "    To add it later: drag $DEST/EyeGuard.app into /Applications."
fi

echo "==> Installing the agent from the new location (will use the .app)"
( cd "$DEST" && ./install_agent.sh )

echo
echo "Migration complete."
echo "  Runtime:  $DEST"
echo "  App:      $APPS/EyeGuard.app  ->  $DEST/EyeGuard.app"
echo
echo "IMPORTANT: EyeGuard.app is a NEW identity, so macOS will ask you to grant it"
echo "  Screen Recording (required) and Accessibility + Automation (for app/site"
echo "  corroboration). The menu bar eye will be GRAY until Screen Recording is on."
echo
echo "Once you've confirmed it works, the old copy at:"
echo "  $SRC"
echo "can be deleted."
