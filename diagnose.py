"""Capture the current screen and print the detector's verdict + detail.

Usage:  ./.venv/bin/python diagnose.py
Put the content you want to test on screen first. Prints, per display, the
verdict and the top explicit / suggestive / safe prompt with scores for the
worst (highest-scoring) crop — so you can see what it matched and what it
competed against.
"""

from __future__ import annotations

import sys
import yaml
from pathlib import Path

from eyeguard.capture import ScreenCapturer
from eyeguard.main import build_detector


def main():
    cfg = yaml.safe_load(open(Path(__file__).resolve().parent / "config.yaml"))
    det = build_detector(cfg, verbose=False)
    arb = det.arbiter
    cap = ScreenCapturer(displays=cfg["capture"]["displays"],
                         max_width=cfg["capture"]["max_width"],
                         change_threshold=0.0)
    import torch
    frames = list(cap.capture(skip_unchanged=False))
    if not frames:
        print("No frame captured (screen recording permission?)."); return
    r, y = arb._n_red, arb._n_yellow
    for fr in frames:
        result = det.analyze(fr.image)
        print(f"\n=== display {fr.display_index} -> {result.verdict.value.upper()} "
              f"| {result.reason} ===")
        # Detailed per-crop tier scores.
        crops = [c.convert("RGB") for c in arb._crops(fr.image)]
        with torch.no_grad():
            inp = arb._processor(images=crops, return_tensors="pt").to(arb._device)
            f = arb._model.get_image_features(**inp)
            f = f / f.norm(dim=-1, keepdim=True)
            sims = f @ arb._text_features.T
            grp = torch.stack([sims[:, :r].amax(1), sims[:, r:r+y].amax(1),
                               sims[:, r+y:].amax(1)], 1) * arb._model.logit_scale.exp()
            gp = grp.softmax(1)
        # Worst crop by P(not safe).
        worst = int((gp[:, 0] + gp[:, 1]).argmax())
        where = "full" if worst == 0 else f"tile{worst}"
        pr, ps, psf = gp[worst].tolist()
        be = int(sims[worst, :r].argmax())
        bs = int(sims[worst, r:r+y].argmax())
        bf = int(sims[worst, r+y:].argmax())
        print(f"  worst crop: {where}  P(red)={pr:.2f} P(yellow)={ps:.2f} P(safe)={psf:.2f}")
        print(f"    best explicit : {arb.explicit_prompts[be]}")
        print(f"    best suggestive: {arb.suggestive_prompts[bs]}")
        print(f"    best safe      : {arb.safe_prompts[bf]}   <- needs to win on safe content")


if __name__ == "__main__":
    sys.exit(main())
