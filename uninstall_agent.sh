#!/usr/bin/env bash
# Stop and remove the EyeGuard LaunchAgent (menu bar app).
# Phase 4: requires the partner's pause password. Removing it any other way
# will trip the "monitoring went dark" alert.
set -euo pipefail
DIR="$HOME/Library/Application Support/EyeGuard"
LABEL="com.eyeguard.monitor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$DIR/eg_authorize.sh" ]; then
  # shellcheck source=/dev/null
  source "$DIR/eg_authorize.sh"
  if eg_authorize; then
    eg_clean_beacon                    # authorized -> no gone-dark alert
  else
    echo "❌ Wrong password — EyeGuard was NOT removed."
    echo "   Removing it any other way will alert your accountability partner."
    exit 1
  fi
fi

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL. The menu bar icon will disappear."
else
  echo "Not installed (no $PLIST)."
fi
