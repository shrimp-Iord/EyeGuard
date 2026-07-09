#!/usr/bin/env bash
# Promote the self-contained EyeGuard-bundled.app to /Applications/EyeGuard.app
# and point the login agent at it. Run in Terminal (needs admin for /Applications).
# After this, grant Screen Recording to EyeGuard ONE time — it's then permanent
# (the embedded Python lives at a fixed path inside the app forever).
set -euo pipefail

RUNTIME="$HOME/Library/Application Support/EyeGuard"
SRC="$RUNTIME/EyeGuard-bundled.app"
DST="/Applications/EyeGuard.app"
EXE="$DST/Contents/MacOS/EyeGuard"
LABEL="com.eyeguard.monitor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

[ -d "$SRC" ] || { echo "No bundled app at $SRC — run build_bundled_app.sh first." >&2; exit 1; }

echo "==> Stopping the current agent"
launchctl unload "$PLIST" 2>/dev/null || true
pkill -f "m eyeguard.menubar" 2>/dev/null || true
sleep 1

echo "==> Installing self-contained EyeGuard.app to /Applications (admin password)"
sudo rm -rf "$DST"
sudo cp -R "$SRC" "$DST"
sudo chown -R "$(id -un)":staff "$DST" 2>/dev/null || true

echo "==> Pointing the login agent at the bundled app"
mkdir -p "$RUNTIME/logs"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>            <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$EXE</string>
    </array>
    <key>WorkingDirectory</key> <string>$RUNTIME</string>
    <key>RunAtLoad</key>        <true/>
    <key>KeepAlive</key>        <true/>
    <key>StandardOutPath</key>  <string>$RUNTIME/logs/agent.out.log</string>
    <key>StandardErrorPath</key><string>$RUNTIME/logs/agent.err.log</string>
    <key>ProcessType</key>      <string>Interactive</string>
</dict>
</plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -f "$DST" 2>/dev/null || true

# Clean up the staging copy and the old lightweight app shell to save ~1GB.
rm -rf "$SRC" "$RUNTIME/EyeGuard.app"

echo
echo "Done — EyeGuard now runs from its own embedded Python (self-contained)."
echo
echo "ONE-TIME STEP: the eye in the menu bar will be GRAY until you grant the new"
echo "app Screen Recording. Open System Settings > Privacy & Security >"
echo "Screen Recording, enable EyeGuard (add it with + if needed:"
echo "  $EXE ), then it relaunches and the eye goes green. Permanent after this."
echo
echo "You can also now unpin Homebrew Python (optional):  brew unpin python@3.12"
