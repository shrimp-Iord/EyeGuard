#!/usr/bin/env bash
# Run the EyeGuard Phase 1 detection loop.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "No .venv found. Run ./setup.sh first." >&2
  exit 1
fi
source .venv/bin/activate
exec python -m eyeguard.main "$@"
