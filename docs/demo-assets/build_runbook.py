"""Build RUNBOOK.html — the presenter's stage document.

Reads testdata.json (27 pages of real browser-driven test results gathered
overnight) and emits a single self-contained HTML file: an index, then one page
per module with what to show, exact inputs, likely questions, everything tested,
and what not to touch. Arrow keys move between pages.
"""
import json, io, html, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(io.open(os.path.join(HERE, "testdata.json"), encoding="utf-8"))

LOCAL = "http://localhost:8080"
LIVE = "https://ominous-space-happiness-wrqrp69j95jv3g6-8080.app.github.dev"

# Presentation order: the route a presenter actually walks, not alphabetical.
ORDER = [
    "Login / auth", "Sign-in screen", "Command Dashboard",
    "VisionScan / Text", "VisionScan / Object", "VisionScan / Reference",
    "VisionScan / Suspect", "VisionScan / Scene", "VisionScan / Camera Feeds",
    "PDF investigation", "Live Alerts", "City Map",
    "Arbiter", "CrimeGPT", "Legal Feed",
    "Cases", "Complaints", "Citizen portal — public", "Citizen portal (",
    "Admin / danger", "Admin", "RBAC",
    "Language switching", "Mobile / field", "App shell",
    ]

def rank(p):
    n = p["name"]
    for i, pre in enumerate(ORDER):
        if n.startswith(pre):
            return i
    return len(ORDER)

# Two of the tested "pages" are QA reports about the testing itself, not screens
# a presenter opens. They are the right output for a test run and the wrong thing
# to have in front of you on stage, so they do not ship in the runbook.
QA_ONLY = ("COVERAGE GAPS", "404 / dead-end")
DATA = [d for d in DATA if not d["name"].startswith(QA_ONLY)]

# One agent named the camera rail just "VisionScan", which is useless in a sidebar
# that already has five VisionScan entries.
for d in DATA:
    if d["name"].startswith("VisionScan — Camera Feeds"):
        d["name"] = "VisionScan / Camera Feeds rail"
    if d["name"].startswith("Admin — the two buttons"):
        d["name"] = "Admin / danger zone — security tab"

PAGES = sorted(DATA, key=rank)

def e(s):
    return html.escape(str(s or ""))

def short(name):
    """Nav label: trim the explanatory tail after an em-dash or bracket."""
    n = re.split(r"\s+[—(]", name)[0].strip()
    return n if len(n) <= 34 else n[:32] + "…"


def _disambiguate(pages):
    """Two agents can name their page the same thing ("Admin", "Citizen portal").
    Identical sidebar entries are useless mid-presentation, so when labels collide
    keep a distinguishing fragment of the fuller name."""
    seen = {}
    for p in pages:
        lbl = short(p["name"])
        seen.setdefault(lbl, []).append(p)
    for lbl, group in seen.items():
        if len(group) < 2:
            for p in group:
                p["_nav"] = lbl
            continue
        for p in group:
            tail = p["name"][len(lbl):].strip(" —·:()")
            tail = re.sub(r"^(the\s+)", "", tail)
            p["_nav"] = (lbl + " · " + tail[:24]).strip(" ·") if tail else lbl

STATUS = {"pass": ("ok", "PASS"), "fail": ("bad", "FAIL"),
          "partial": ("warn", "PARTIAL"), "not-applicable": ("na", "N/A")}

def render_page(p, i, total):
    i = i + 2  # slots 0 and 1 are the written START HERE and FAQ pages
    n = p["name"]
    fails = [t for t in p.get("tested", []) if t.get("status") == "fail"]
    parts = [f'<section class="page" id="p{i}" data-name="{e(n)}">']
    parts.append(f'<div class="crumb">{i-1} of {total}</div>')
    parts.append(f"<h1>{e(n)}</h1>")
    if p.get("one_liner"):
        parts.append(f'<p class="lede">{e(p["one_liner"])}</p>')
    if p.get("route"):
        parts.append(f'<div class="route"><b>Get there:</b> {e(p["route"])}</div>')

    # ---- what to show (the part read on stage) ----
    if p.get("headline"):
        parts.append('<h2 class="h-show">Show this</h2><ol class="show">')
        for hl in p["headline"][:3]:
            parts.append("<li>")
            parts.append(f'<div class="what">{e(hl.get("what"))}</div>')
            if hl.get("exact_steps"):
                parts.append(f'<div class="steps"><b>Do:</b> {e(hl["exact_steps"])}</div>')
            if hl.get("why_impressive"):
                parts.append(f'<div class="why">{e(hl["why_impressive"])}</div>')
            parts.append("</li>")
        parts.append("</ol>")

    # ---- copy-pasteable inputs ----
    if p.get("inputs"):
        parts.append('<h2 class="h-in">Exact inputs</h2><table class="inputs"><thead>'
                     "<tr><th>Field</th><th>Value — click to copy</th><th>What you should get</th></tr>"
                     "</thead><tbody>")
        for it in p["inputs"][:6]:
            v = e(it.get("value"))
            parts.append(
                f'<tr><td class="f">{e(it.get("field"))}</td>'
                f'<td><code class="copy" title="click to copy">{v}</code></td>'
                f'<td class="x">{e(it.get("expected"))}</td></tr>')
        parts.append("</tbody></table>")

    # ---- questions ----
    if p.get("questions"):
        parts.append('<h2 class="h-q">If they ask</h2><div class="qa">')
        for q in p["questions"][:6]:
            parts.append(f'<details><summary>{e(q.get("q"))}</summary>'
                         f'<div class="ans">{e(q.get("a"))}</div></details>')
        parts.append("</div>")

    # ---- warnings ----
    # Two filters. Anything describing a bug we fixed overnight is now FALSE and
    # must not be on a stage card. And anything that is QA bookkeeping rather
    # than presenter guidance is noise the presenter has to read past.
    FIXED = ("rate limit", "429", "thumbnail", "sign out all", "sign-out",
             "bottom nav", "unlabelled", "notification panel", "zone-analytics",
             "line-crossings", "no auth", "without auth", "qa probe", "qa test",
             "qa artefact", "qa pollution", "truncat", "stale", "your report",
             "your script", "coverage", "nobody tested", "did not test")
    kept = [b for b in p.get("broken", [])
            if not any(f in b.lower() for f in FIXED)][:4]
    p["broken"] = kept
    if p.get("broken"):
        parts.append('<h2 class="h-warn">Careful / known limits</h2><ul class="warn">')
        for b in p["broken"]:
            parts.append(f"<li>{e(b)}</li>")
        parts.append("</ul>")

    # ---- numbers ----
    if p.get("numbers"):
        parts.append('<h2 class="h-num">Measured numbers you can quote</h2><ul class="nums">')
        for x in p["numbers"]:
            parts.append(f"<li>{e(x)}</li>")
        parts.append("</ul>")

    prev = f'<a class="nav prev" href="#p{i-1}">← {e(PAGES[i-3]["_nav"]) if i>2 else "Common questions"}</a>'
    nxt = f'<a class="nav next" href="#p{i+1}">{e(PAGES[i-1]["_nav"])} →</a>' if i-1 < total else "<span></span>"
    parts.append(f'<div class="pager">{prev}{nxt}</div></section>')
    return "".join(parts)

_disambiguate(PAGES)

total = len(PAGES)
nav = ('<li><a href="#p0" data-i="0"><span class="ni">0</span>Start here</a></li>'
       '<li><a href="#p1" data-i="1"><span class="ni">Q</span>Common questions</a></li>') + "".join(
    f'<li><a href="#p{i+2}" data-i="{i+2}"><span class="ni">{i+1}</span>{e(p["_nav"])}'
    + "</a></li>"
    for i, p in enumerate(PAGES))

tot_tested = sum(len(p.get("tested", [])) for p in PAGES)
tot_pass = sum(1 for p in PAGES for t in p.get("tested", []) if t.get("status") == "pass")
tot_q = sum(len(p.get("questions", [])) for p in PAGES)
tot_in = sum(len(p.get("inputs", [])) for p in PAGES)

pages_html = "".join(render_page(p, i, total) for i, p in enumerate(PAGES))

import sys
sys.path.insert(0, HERE)
from runbook_template import document
import runbook_template
from runbook_intro import intro_page, EXTRA_CSS
from runbook_faq import faq_page, FAQ
runbook_template.CSS += EXTRA_CSS

tot_fail = sum(1 for p in PAGES for t in p.get("tested", []) if t.get("status") == "fail")
pages_html = (intro_page(total, tot_tested, tot_pass, tot_fail, "Common questions")
              + faq_page("Start here", PAGES[0]["_nav"], 0, 2)
              + pages_html)

DOC = document(total=total, tot_tested=tot_tested, tot_pass=tot_pass,
               tot_in=tot_in, tot_q=tot_q, nav=nav, pages_html=pages_html,
               local=LOCAL, live=LIVE)

out = os.path.abspath(os.path.join(HERE, "..", "..", "RUNBOOK.html"))
io.open(out, "w", encoding="utf-8").write(DOC)
print("wrote " + out)
print("  %d pages | %d controls (%d pass) | %d inputs | %d questions"
      % (total, tot_tested, tot_pass, tot_in, tot_q))
print("  %.0f KB" % (len(DOC) / 1024))
