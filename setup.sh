#!/usr/bin/env bash
# EyeGuard setup: create an isolated Python 3.12 venv and install dependencies.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-/opt/homebrew/bin/python3.12}"
if [ ! -x "$PYTHON" ]; then
  echo "Python 3.12 not found at $PYTHON. Install with: brew install python@3.12" >&2
  exit 1
fi

echo "==> Creating virtualenv (.venv) with $($PYTHON --version)"
"$PYTHON" -m venv .venv
source .venv/bin/activate

echo "==> Upgrading pip"
pip install --quiet --upgrade pip

echo "==> Installing core dependencies (this downloads onnxruntime/opencv; takes a bit)"
pip install -r requirements.txt

echo
echo "==> Done. Core pipeline installed."
echo
echo "Stage 2 arbiter (optional):"
echo "  Off by default. To enable nuanced arbitration of borderline frames, set"
echo "  'arbiter.enabled: true' in config.yaml. First run auto-downloads moondream2"
echo "  (~4GB, cached) and uses ~4GB RAM while loaded — fine on 8GB intermittently."
echo "  Until enabled, borderline frames are logged as 'review' (pipeline still runs)."
echo
echo "Next: grant Screen Recording permission to your terminal, then run ./run.sh --once"
