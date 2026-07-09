#!/usr/bin/env bash
# Stop and remove the EyeGuard LaunchAgent (menu bar app).
set -euo pipefail
LABEL="com.eyeguard.monitor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL. The menu bar icon will disappear."
else
  echo "Not installed (no $PLIST)."
fi
