#!/usr/bin/env bash
# The PARTNER runs this to set (or change) the pause password.
# Input is hidden and only the SHA-256 HASH is produced. The monitored user
# never sees the password and can't reverse the hash — so even the person
# running the Supabase SQL Editor only ever handles the hash.
set -euo pipefail

read -r -s -p "New pause password: " p1; echo
read -r -s -p "Confirm password:   " p2; echo
[ -n "$p1" ] || { echo "Empty password — aborted."; exit 1; }
[ "$p1" = "$p2" ] || { echo "Passwords didn't match — aborted."; exit 1; }

hash=$(printf '%s' "$p1" | shasum -a 256 | awk '{print $1}')
echo
echo "Done. Paste THIS line into the Supabase SQL Editor and Run:"
echo
echo "  update public.settings set pause_password_hash = '$hash' where id = 1;"
echo
echo "(That's a one-way hash of your password — it can't be reversed.)"
