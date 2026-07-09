"""Render the JSONL flag log into a human-readable text file.

Keeps flags.jsonl as the single machine-readable source of truth (retention
operates on it) and generates a readable view on demand for the menu bar's
"Open flag log".
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_EMOJI = {"flagged": "🔴", "alert": "🟡", "review": "⚪"}
_LABEL = {"flagged": "REVEALING", "alert": "suggestive", "review": "review"}


def _fmt_record(rec: dict) -> str:
    # UTC ISO -> local, human time.
    try:
        ts = datetime.fromisoformat(rec["timestamp"]).astimezone()
        when = ts.strftime("%Y-%m-%d %I:%M:%S %p")
    except Exception:
        when = rec.get("timestamp", "?")
    v = rec.get("verdict", "?")
    emoji = _EMOJI.get(v, "•")
    label = _LABEL.get(v, v)

    app = rec.get("app") or "unknown app"
    where = rec.get("url") or rec.get("window_title")
    location = f"  ·  {where}" if where else ""

    # Pull the human bits out of the reason string (e.g. clip-yellow:0.92:tile5:...).
    reason = rec.get("reason", "")
    detail = reason.split("->")[-1].strip() if "->" in reason else reason

    return (f"{when}   {emoji} {label:9}  {app}{location}\n"
            f"        {detail}")


def write_readable(flag_log: str | Path, out_path: str | Path,
                   newest_first: bool = True) -> Path:
    src = Path(flag_log)
    out = Path(out_path)
    records = []
    if src.exists():
        with src.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if newest_first:
        records = records[::-1]

    reds = sum(1 for r in records if r.get("verdict") == "flagged")
    yellows = sum(1 for r in records if r.get("verdict") == "alert")
    header = (f"EyeGuard flag log — generated {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
              f"{len(records)} entries  ·  {reds} explicit (red)  ·  {yellows} suggestive (yellow)\n"
              f"(newest first)\n"
              + "=" * 72 + "\n\n")
    with out.open("w") as f:
        f.write(header)
        if not records:
            f.write("No flags recorded.\n")
        for r in records:
            f.write(_fmt_record(r) + "\n\n")
    return out


# ---------------------------------------------------------------------------
# Branded HTML report — for a non-technical accountability partner to skim.
# ---------------------------------------------------------------------------

# The eye logo (white), inlined so the report is a single self-contained file.
_EYE_SVG = (
    '<svg viewBox="0 0 100 100" width="34" height="34" fill="none">'
    '<path stroke="#fff" stroke-width="2.5" d="M5.5,50 C25.5,21 74.5,21 94.5,50 '
    'C74.5,79 25.5,79 5.5,50 Z"/><path fill="#fff" fill-rule="evenodd" '
    'd="M12.5,50 C31,28 69,28 87.5,50 C69,72 31,72 12.5,50 Z M45.5,49 A5.5,5.5 '
    '0 1 1 54.5,49 L53,57.5 L47,57.5 Z"/></svg>'
)


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _local(rec: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(rec["timestamp"]).astimezone()
    except Exception:
        return None


def _what(rec: dict) -> str:
    """Plain-language description of what was detected.

    RED is the immediate-alert tier (very revealing OR nude). CLIP can't reliably
    tell a string bikini from nudity, so we DON'T parrot its raw "exposed
    genitals" match — that would mislabel clothed-but-revealing content as nudity.
    Show an honest generic line and let the thumbnail show the specifics.
    """
    if rec.get("verdict") == "flagged":
        # NudeNet (trained nudity detector, runs first) fires on ACTUAL exposed
        # body parts, not bikinis — so a nudenet hit means real nudity.
        if (rec.get("reason") or "").startswith("nudenet"):
            return "explicit nudity / exposed body — see image"
        return "very revealing content — see image"
    # YELLOW: the matched suggestive concept is accurate (bikini, gym, etc.).
    reason = rec.get("reason", "")
    if ":" in reason:
        tail = reason.split(":")[-1].strip()
    elif reason.startswith("nudenet"):
        tail = "exposed skin"
    else:
        tail = reason.strip()
    return _esc(tail or "flagged content")


def _where(rec: dict) -> str:
    app = rec.get("app") or "an app"
    loc = rec.get("url") or rec.get("window_title")
    return _esc(app) + (f" — {_esc(loc)}" if loc else "")


def _thumb(rec: dict, report_dir: Path) -> str:
    """A small thumbnail <img> if the flagged frame was saved to disk."""
    p = rec.get("saved_frame")
    if not p:
        return ""
    path = Path(p)
    if not path.is_absolute():
        path = report_dir / path
    if not path.exists():
        return ""
    # file:// URL so it loads regardless of how the report was opened.
    return f'<img class="thumb" src="file://{_esc(str(path))}" loading="lazy">'


def write_html_report(flag_log: str | Path, out_path: str | Path,
                      days: int = 7, refresh: int = 0) -> Path:
    src, out = Path(flag_log), Path(out_path)
    records = []
    if src.exists():
        with src.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    reds = sum(1 for r in records if r.get("verdict") == "flagged")
    yellows = sum(1 for r in records if r.get("verdict") == "alert")
    now = datetime.now()

    # Group rows by local day.
    rows_by_day: dict[str, list[str]] = {}
    order: list[str] = []
    for r in records:
        dt = _local(r)
        if dt is None:
            continue
        day = dt.strftime("%A, %B %-d")
        if day not in rows_by_day:
            rows_by_day[day] = []
            order.append(day)
        verdict = r.get("verdict", "")
        sev_cls = "red" if verdict == "flagged" else "yellow"
        if verdict == "flagged":
            sev_txt = ("Nudity" if (r.get("reason") or "").startswith("nudenet")
                       else "Revealing")
        else:
            sev_txt = "Suggestive"
        grade = r.get("grade") or ""
        gcls = {"Likely": "g-hi", "Possible": "g-mid",
                "Borderline": "g-lo"}.get(grade, "")
        grade_html = (f'<span class="grade {gcls}">{grade}</span>'
                      if grade else "")
        rows_by_day[day].append(
            f'<div class="row {sev_cls}">'
            f'{_thumb(r, out.parent)}'
            f'<div class="meta">'
            f'<div class="rtop"><span class="time">{dt.strftime("%-I:%M %p")}</span>'
            f'<span class="pill {sev_cls}">{sev_txt}</span>{grade_html}'
            f'<span class="where">{_where(r)}</span></div>'
            f'<div class="what">{_what(r)}</div></div>'
            f'</div>')

    sections = ""
    for day in order:
        sections += (f'<section class="day"><h2>{day}'
                     f'<span class="daycount">{len(rows_by_day[day])}</span></h2>'
                     + "".join(rows_by_day[day]) + "</section>")
    if not records:
        sections = ('<div class="empty">NO ACTIVITY FLAGGED — ALL CLEAR ✓</div>')

    refresh_tag = (f'<meta http-equiv="refresh" content="{refresh}">'
                   if refresh and refresh > 0 else "")
    live_tag = ('<span class="live"><span class="dot"></span>Live</span>'
                if refresh and refresh > 0 else "")
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{refresh_tag}
<title>EyeGuard Activity Report</title><style>
:root{{--bg:#0b0e12;--card:#151b22;--line:#2a333d;--ink:#eef2f6;--muted:#7e8a98;
--teal:#1b4b63;--red:#e5403a;--yellow:#f2a200;--green:#2fb85c;
--head:"Futura","Jost","Century Gothic","Trebuchet MS",sans-serif;
--body:"Helvetica Neue",Helvetica,Arial,sans-serif;}}
*{{box-sizing:border-box;}}body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.45 var(--body);}}
.wrap{{max-width:780px;margin:0 auto;padding:0 14px 48px;}}
header{{background:linear-gradient(135deg,#1b4b63,#08161f);padding:24px 22px;
border:1px solid var(--line);border-top:none;display:flex;align-items:center;gap:14px;}}
header h1{{font-family:var(--head);font-size:22px;margin:0;font-weight:700;
text-transform:uppercase;letter-spacing:.06em;}}
header .sub{{color:#a9c2cf;font-size:12px;margin-top:3px;text-transform:uppercase;
letter-spacing:.05em;}}
.cards{{display:flex;gap:10px;margin:16px 0 6px;}}
.card{{flex:1;background:var(--card);border:1px solid var(--line);
border-top:3px solid var(--line);padding:16px;}}
.card .n{{font-family:var(--head);font-size:32px;font-weight:700;line-height:1;
letter-spacing:.02em;}}
.card .l{{font-size:11px;color:var(--muted);margin-top:6px;text-transform:uppercase;
letter-spacing:.09em;font-weight:600;}}
.card.red{{border-top-color:var(--red);}}.card.red .n{{color:var(--red);}}
.card.yellow{{border-top-color:var(--yellow);}}.card.yellow .n{{color:var(--yellow);}}
.filters{{display:flex;gap:8px;margin:14px 0 4px;}}
.fbtn{{font-family:var(--head);font-size:12px;font-weight:700;text-transform:uppercase;
letter-spacing:.08em;color:var(--muted);background:var(--card);
border:1px solid var(--line);padding:9px 16px;cursor:pointer;}}
.fbtn.active{{color:var(--ink);border-color:#46c;background:#1d2630;}}
.fbtn[data-sev="red"].active{{border-color:var(--red);color:#ff8a85;}}
.fbtn[data-sev="yellow"].active{{border-color:var(--yellow);color:#ffc24d;}}
h2{{font-family:var(--head);font-size:13px;color:var(--muted);text-transform:uppercase;
letter-spacing:.1em;margin:24px 0 8px;display:flex;align-items:center;gap:8px;
font-weight:700;}}
.daycount{{background:var(--card);border:1px solid var(--line);
padding:2px 9px;font-size:11px;color:var(--muted);}}
.row{{display:flex;align-items:center;gap:12px;background:var(--card);
border:1px solid var(--line);border-left:4px solid var(--line);
padding:10px 14px;margin-bottom:6px;}}
.row.red{{border-left-color:var(--red);}}.row.yellow{{border-left-color:var(--yellow);}}
.thumb{{width:104px;height:64px;object-fit:cover;border:1px solid var(--line);
flex:none;background:#000;cursor:pointer;}}
.thumb:hover{{outline:2px solid #46c;}}
.meta{{flex:1;min-width:0;}}
.rtop{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}}
.time{{font-family:var(--head);color:var(--muted);font-size:12px;width:78px;flex:none;
letter-spacing:.03em;}}
.pill{{font-family:var(--head);font-size:10.5px;font-weight:700;padding:3px 10px;
flex:none;text-transform:uppercase;letter-spacing:.06em;}}
.pill.red{{background:rgba(229,64,58,.18);color:#ff8a85;}}
.pill.yellow{{background:rgba(242,162,0,.18);color:#ffc24d;}}
.grade{{font-family:var(--head);font-size:10px;font-weight:700;padding:3px 8px;
flex:none;text-transform:uppercase;letter-spacing:.06em;border:1px solid var(--line);}}
.grade.g-hi{{color:#ff8a85;border-color:#5a2b2b;}}
.grade.g-mid{{color:#ffc24d;border-color:#5a4a1f;}}
.grade.g-lo{{color:var(--muted);}}
.where{{font-weight:700;font-size:13.5px;}}
.what{{color:var(--muted);font-size:12px;margin-top:4px;}}
.live{{display:inline-flex;align-items:center;gap:6px;color:var(--green);
font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin-left:auto;}}
.dot{{width:8px;height:8px;border-radius:50%;background:var(--green);
animation:pulse 1.4s infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:.25;}}}}
.empty{{font-family:var(--head);text-align:center;color:var(--green);padding:60px 0;
font-size:18px;letter-spacing:.05em;}}
footer{{color:var(--muted);font-size:11px;text-align:center;margin-top:32px;
line-height:1.8;text-transform:uppercase;letter-spacing:.04em;}}
/* filtering (CSS :has() hides days that end up empty) */
body[data-filter="red"] .row.yellow{{display:none;}}
body[data-filter="yellow"] .row.red{{display:none;}}
body[data-filter="red"] .day:not(:has(.row.red)){{display:none;}}
body[data-filter="yellow"] .day:not(:has(.row.yellow)){{display:none;}}
</style></head><body data-filter="all"><div class="wrap">
<header>{_EYE_SVG}<div><h1>EyeGuard Report</h1>
<div class="sub">Updated {now.strftime('%-I:%M:%S %p')} · last {days} days</div></div>{live_tag}</header>
<div class="cards">
<div class="card"><div class="n">{len(records)}</div><div class="l">Total flags</div></div>
<div class="card red"><div class="n">{reds}</div><div class="l">Revealing</div></div>
<div class="card yellow"><div class="n">{yellows}</div><div class="l">Suggestive</div></div>
</div>
<div class="filters">
<button class="fbtn active" data-sev="all" onclick="flt('all')">All</button>
<button class="fbtn" data-sev="red" onclick="flt('red')">Revealing</button>
<button class="fbtn" data-sev="yellow" onclick="flt('yellow')">Suggestive</button>
</div>
{sections}
<footer>Watches the screen locally on this Mac — nothing leaves the device<br>
History auto-deletes after {days} days · Revealing = immediate-alert (very revealing or nude) · Suggestive = mildly revealing / borderline</footer>
</div><script>
function flt(s){{document.body.dataset.filter=s;
document.querySelectorAll('.fbtn').forEach(function(b){{
b.classList.toggle('active',b.dataset.sev===s);}});
try{{localStorage.setItem('eg_filter',s);}}catch(e){{}}}}
// restore the chosen filter across the live auto-refresh
try{{var s=localStorage.getItem('eg_filter');if(s&&s!=='all')flt(s);}}catch(e){{}}
// click a thumbnail to open the full frame
document.querySelectorAll('.thumb').forEach(function(t){{
t.onclick=function(){{window.open(t.src,'_blank');}};}});
</script></body></html>"""
    out.write_text(html)
    return out
