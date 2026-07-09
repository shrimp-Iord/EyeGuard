#!/usr/bin/env bash
# Install EyeGuard as a per-user LaunchAgent so the menu bar app starts at login
# and keeps running with no terminal open. Re-run any time to update it.
set -euo pipefail
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
APP_EXE="$PROJECT_DIR/EyeGuard.app/Contents/MacOS/EyeGuard"
LABEL="com.eyeguard.monitor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ ! -x "$PYTHON" ]; then
  echo "No venv at $PYTHON — run ./setup.sh first." >&2
  exit 1
fi

# Decide how to launch. A .app bundle is the clean identity, but macOS TCC-gates
# bundles out of protected folders (~/Desktop, ~/Documents, ~/Downloads), where
# the bare CLI python still works. So: use the .app only outside those folders.
PROTECTED=0
case "$PROJECT_DIR/" in
  "$HOME/Desktop/"*|"$HOME/Documents/"*|"$HOME/Downloads/"*) PROTECTED=1;;
esac

if [ -x "$APP_EXE" ] && [ "$PROTECTED" -eq 0 ]; then
  PROG_ARGS="        <string>$APP_EXE</string>"
  LAUNCH_DESC="EyeGuard.app (clean identity)"
else
  PROG_ARGS="        <string>$PYTHON</string>
        <string>-m</string>
        <string>eyeguard.menubar</string>"
  LAUNCH_DESC="CLI python"
  [ -x "$APP_EXE" ] && [ "$PROTECTED" -eq 1 ] && echo \
    "Note: project is under a protected folder; launching via CLI python (the .app would be TCC-blocked here)."
fi

mkdir -p "$HOME/Library/LaunchAgents" "$PROJECT_DIR/logs"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>            <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
$PROG_ARGS
    </array>
    <key>WorkingDirectory</key> <string>$PROJECT_DIR</string>
    <!-- Start at login and relaunch if it ever exits (tamper-evidence seed). -->
    <key>RunAtLoad</key>        <true/>
    <key>KeepAlive</key>        <true/>
    <key>StandardOutPath</key>  <string>$PROJECT_DIR/logs/agent.out.log</string>
    <key>StandardErrorPath</key><string>$PROJECT_DIR/logs/agent.err.log</string>
    <key>ProcessType</key>      <string>Interactive</string>
</dict>
</plist>
PLIST_EOF

# Reload cleanly whether or not it was already loaded.
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "Installed and started: $LABEL  (via $LAUNCH_DESC)"
echo "  plist:  $PLIST"
echo "  logs:   $PROJECT_DIR/logs/agent.{out,err}.log"
echo
echo "A 🟢 EyeGuard icon should appear in your menu bar within a few seconds."
echo "First launch will prompt for Screen Recording (required) and, for app/site"
echo "corroboration, Accessibility + Automation permissions. Grant them, then the"
echo "agent will relaunch automatically."
echo
echo "To stop/remove it later:  ./uninstall_agent.sh"
