"""On-screen text + browsing-signal analysis.

EyeGuard's image detector is blind to the TEXTUAL side of behavior — erotic
text, sexual chat, explicit search terms — because there's no nude *image* to
classify. This adds two cheap, on-device checks that close that gap:

  * OCR the captured frame (Apple's Vision framework, local, no network) and
    flag when enough explicit terms appear.
  * Match explicit terms in the active URL / window title (search queries show
    up there), flagging the site as a signal in its own right.

Word-boundary matching avoids false hits like "sex" inside "Middlesex".
"""

from __future__ import annotations

import io
import re


def ocr(pil_image) -> str:
    """Recognize on-screen text via Apple Vision (on-device). '' on any failure."""
    try:
        import Vision
        import Foundation
        buf = io.BytesIO()
        pil_image.save(buf, "PNG")
        raw = buf.getvalue()
        data = Foundation.NSData.dataWithBytes_length_(raw, len(raw))
        handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(
            data, None)
        req = Vision.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLevel_(1)         # 1 = fast (plenty for screen text)
        req.setUsesLanguageCorrection_(False)
        handler.performRequests_error_([req], None)
        lines = []
        for obs in (req.results() or []):
            cand = obs.topCandidates_(1)
            if cand:
                lines.append(str(cand[0].string()))
        return "\n".join(lines)
    except Exception:
        return ""


def match_terms(text: str, terms: list[str]) -> list[str]:
    """Distinct explicit terms present in `text`, matched on word boundaries."""
    if not text:
        return []
    low = text.lower()
    hits = []
    for t in terms:
        t = str(t).lower()
        if re.search(r"\b" + re.escape(t) + r"\b", low):
            hits.append(t)
    return hits
