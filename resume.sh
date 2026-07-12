#!/usr/bin/env bash
# Restart EyeGuard after a pause. No password needed — resuming is always allowed.
set -euo pipefail
LABEL="com.eyeguard.monitor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
if [ ! -f "$PLIST" ]; then
  echo "EyeGuard isn't installed (no $PLIST). Run ./install_agent.sh."
  exit 1
fi
launchctl load "$PLIST" 2>/dev/null \
  || launchctl kickstart -k "gui/$(id -u)/$LABEL" 2>/dev/null || true
echo "✅ EyeGuard resumed — the heartbeat will be back within a minute."
