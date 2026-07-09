#!/usr/bin/env bash
# Generate EyeGuard icon assets from EyeGuard-logo.svg:
#   - menu bar eyes tinted by state (green/yellow/red/gray) -> assets/menubar/
#   - app icon -> assets/EyeGuard.icns
# Requires: rsvg-convert (brew install librsvg), sips + iconutil (macOS built-in).
set -euo pipefail
cd "$(dirname "$0")"

SRC="EyeGuard-logo.svg"
[ -f "$SRC" ] || { echo "Missing $SRC" >&2; exit 1; }
mkdir -p assets/menubar assets/_tmp

# --- menu bar icons: tint the eye per state -------------------------------
# The logo uses currentColor for stroke+fill, so we substitute a hex color.
make_menubar() {
  local name="$1" color="$2"
  local svg="assets/_tmp/eye_${name}.svg"
  sed "s/currentColor/${color}/g" "$SRC" > "$svg"
  # 44px @2x for a crisp ~22pt menu bar glyph.
  rsvg-convert -w 44 -h 44 "$svg" -o "assets/menubar/eye_${name}.png"
}
make_menubar green "#30B85C"    # watching, clear
make_menubar yellow "#F0A500"   # suggestive seen recently
make_menubar red    "#E53935"   # explicit seen recently
make_menubar gray   "#8E8E93"   # not watching / no screen access

# --- app icon -------------------------------------------------------------
# Compose the white eye on a dark rounded-square background at 1024, then build
# the full iconset and pack it into an .icns.
APP_SVG="assets/_tmp/app_icon.svg"
EYE_PATHS=$(sed -n 's/.*\(<path[^>]*d="[^"]*"[^>]*>\).*/\1/p' "$SRC" || true)
cat > "$APP_SVG" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1B4B63"/>
      <stop offset="1" stop-color="#0A1E2A"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="1024" height="1024" rx="225" ry="225" fill="url(#bg)"/>
  <g transform="translate(202,202) scale(6.2)" fill="none">
    <path stroke="#FFFFFF" stroke-width="2.5" d="M5.5,50 C25.5,21 74.5,21 94.5,50 C74.5,79 25.5,79 5.5,50 Z"/>
    <path fill="#FFFFFF" fill-rule="evenodd" d="M12.5,50 C31,28 69,28 87.5,50 C69,72 31,72 12.5,50 Z M45.5,49 A5.5,5.5 0 1 1 54.5,49 L53,57.5 L47,57.5 Z"/>
  </g>
</svg>
SVG

ICONSET="assets/_tmp/EyeGuard.iconset"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
rsvg-convert -w 1024 -h 1024 "$APP_SVG" -o assets/_tmp/icon_1024.png
for sz in 16 32 64 128 256 512 1024; do
  sips -z $sz $sz assets/_tmp/icon_1024.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
done
# @2x variants iconutil expects.
cp "$ICONSET/icon_32x32.png"   "$ICONSET/icon_16x16@2x.png"
cp "$ICONSET/icon_64x64.png"   "$ICONSET/icon_32x32@2x.png"
cp "$ICONSET/icon_256x256.png" "$ICONSET/icon_128x128@2x.png"
cp "$ICONSET/icon_512x512.png" "$ICONSET/icon_256x256@2x.png"
cp "$ICONSET/icon_1024x1024.png" "$ICONSET/icon_512x512@2x.png"
iconutil -c icns "$ICONSET" -o assets/EyeGuard.icns

echo "Built:"
echo "  assets/menubar/eye_{green,yellow,red,gray}.png"
echo "  assets/EyeGuard.icns"
