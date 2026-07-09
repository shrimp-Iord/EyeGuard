"""EyeGuard — local-only screen-content accountability monitor for macOS."""

# Run fully OFFLINE. The CLIP/NudeNet weights are cached locally after first use,
# so force transformers/huggingface to never touch the network (no update checks,
# no timeouts) — EyeGuard then works with no internet at all. Set BEFORE any
# transformers import. (To intentionally re-download/swap a model later, run once
# with HF_HUB_OFFLINE=0.)
import os as _os

_os.environ.setdefault("HF_HUB_OFFLINE", "1")
_os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

__version__ = "0.2.0"
