#!/usr/bin/env bash
# Build EyeGuard.app — a proper macOS app bundle (menu-bar only) that launches
# the EyeGuard engine from the project venv. Gives EyeGuard a stable identity and
# icon, so Screen Recording is attributed to "EyeGuard" rather than "Python".
set -euo pipefail
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
APP="$PROJECT_DIR/EyeGuard.app"
PY="$PROJECT_DIR/.venv/bin/python"

[ -x "$PY" ] || { echo "No venv — run ./setup.sh first." >&2; exit 1; }
[ -f "$PROJECT_DIR/assets/EyeGuard.icns" ] || { echo "No icon — run ./build_icons.sh first." >&2; exit 1; }

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp "$PROJECT_DIR/assets/EyeGuard.icns" "$APP/Contents/Resources/EyeGuard.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>            <string>EyeGuard</string>
    <key>CFBundleDisplayName</key>     <string>EyeGuard</string>
    <key>CFBundleIdentifier</key>      <string>com.eyeguard.monitor</string>
    <key>CFBundleExecutable</key>      <string>EyeGuard</string>
    <key>CFBundleIconFile</key>        <string>EyeGuard</string>
    <key>CFBundlePackageType</key>     <string>APPL</string>
    <key>CFBundleVersion</key>         <string>0.1.0</string>
    <key>CFBundleShortVersionString</key><string>0.1.0</string>
    <!-- Menu-bar-only agent: no Dock icon, no app-switcher entry. -->
    <key>LSUIElement</key>             <true/>
    <key>NSHighResolutionCapable</key> <true/>
</dict>
</plist>
PLIST

# Launcher: run the engine as a CHILD process (no exec) so the bundle remains the
# responsible process for TCC (Screen Recording) attribution. Absolute paths are
# baked in at build time.
cat > "$APP/Contents/MacOS/EyeGuard" <<LAUNCH
#!/bin/bash
cd "$PROJECT_DIR" || exit 1
"$PY" -m eyeguard.menubar
LAUNCH
chmod +x "$APP/Contents/MacOS/EyeGuard"

# Register with LaunchServices so the icon/identity are picked up immediately.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -f "$APP" 2>/dev/null || true

echo "Built $APP"
echo "Launch test:  open \"$APP\"   (or reinstall the agent: ./install_agent.sh)"
