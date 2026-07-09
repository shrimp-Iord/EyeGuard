"""Local flag logging.

Phase 1 writes flag events to a local JSONL file. No network, no partner
notification yet (that's Phase 2). Optionally saves the flagged frame to disk
for sensitivity tuning — off by default for privacy.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageFilter

from .detector import Detection, Verdict


class FlagLogger:
    def __init__(self, flag_log: str, save_flagged_frames: bool = False,
                 flagged_frames_dir: str = "flagged_frames",
                 blur_red_frames: bool = True, blur_strength: int = 50):
        self.flag_log = Path(flag_log)
        self.save_flagged_frames = save_flagged_frames
        self.flagged_frames_dir = Path(flagged_frames_dir)
        # RED-tier frames (nudity / very revealing) are saved BLURRED so a
        # partner can review the flag without being exposed to the content.
        self.blur_red_frames = blur_red_frames
        # Blur radius = image_width / blur_strength. HIGHER = LIGHTER blur.
        self.blur_strength = max(8, int(blur_strength))

    def log(self, detection: Detection, display_index: int,
            image: Image.Image | None = None,
            context: dict | None = None,
            grade: str | None = None, risk: str | None = None) -> dict:
        ts = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": ts,
            "verdict": detection.verdict.value,
            "reason": detection.reason,
            "top_score": round(detection.top_score, 4),
            "labels": {k: round(v, 4) for k, v in detection.labels.items()},
            "arbiter_answer": detection.arbiter_answer,
            "display": display_index,
            # Local corroboration: what app/site/window was active at flag time.
            "app": (context or {}).get("app"),
            "url": (context or {}).get("url"),
            "window_title": (context or {}).get("window_title"),
            # Context-aware risk grade.
            "grade": grade,
            "risk": risk,
        }
        if (self.save_flagged_frames and image is not None
                and detection.verdict in (Verdict.FLAGGED, Verdict.ALERT)):
            self.flagged_frames_dir.mkdir(parents=True, exist_ok=True)
            fname = ts.replace(":", "-") + f"_{detection.verdict.value}_d{display_index}.jpg"
            path = self.flagged_frames_dir / fname
            out_img = image.convert("RGB")
            # Blur RED-tier (nudity/very revealing) frames for safe partner review:
            # body detail is obscured, but the scene/app stays recognizable enough
            # to confirm the flag isn't a false positive.
            if detection.verdict is Verdict.FLAGGED and self.blur_red_frames:
                radius = max(6, out_img.width // self.blur_strength)
                out_img = out_img.filter(ImageFilter.GaussianBlur(radius))
            out_img.save(path, "JPEG", quality=80)
            record["saved_frame"] = str(path)

        with self.flag_log.open("a") as f:
            f.write(json.dumps(record) + "\n")
        return record
