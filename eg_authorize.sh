#!/usr/bin/env bash
# Shared helper: verify the partner's pause password against the cloud, and send
# a clean-shutdown beacon so an AUTHORIZED stop doesn't trip a gone-dark alert.
# Sourced by pause.sh and uninstall_agent.sh.

EG_URL="https://ucgldleacehxjjwwqomk.supabase.co"
EG_DIR="$HOME/Library/Application Support/EyeGuard"

# Prompt for the partner password and check it server-side. Returns 0 if valid.
eg_authorize() {
  local secret pw body ok
  secret=$(cat "$EG_DIR/.supabase_secret" 2>/dev/null) || {
    echo "EyeGuard: secret key not found." >&2; return 1; }
  read -r -s -p "Partner pause password: " pw; echo
  # JSON-encode the password safely (handles quotes/specials).
  body=$(printf '%s' "$pw" | python3 -c \
        'import json,sys;print(json.dumps({"pw":sys.stdin.read()}))')
  ok=$(curl -s -X POST "$EG_URL/rest/v1/rpc/eg_check_pause" \
        -H "apikey: $secret" -H "Authorization: Bearer $secret" \
        -H "Content-Type: application/json" -d "$body")
  [ "$ok" = "true" ]
}

# Tell the watchdog this stop is authorized, so no "went dark" alert fires.
eg_clean_beacon() {
  local secret now
  secret=$(cat "$EG_DIR/.supabase_secret" 2>/dev/null) || return 0
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  curl -s -X POST "$EG_URL/rest/v1/device_status" \
    -H "apikey: $secret" -H "Authorization: Bearer $secret" \
    -H "Content-Type: application/json" \
    -H "Prefer: resolution=merge-duplicates" \
    -d "{\"id\":1,\"status\":\"clean_shutdown\",\"last_heartbeat\":\"$now\"}" \
    >/dev/null 2>&1 || true
}
