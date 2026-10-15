Paste everything below this line into Gemini (or Claude, or GPT — any model
good at visual design) to get a GUI redesign for PocketMind, the offline
on-device demo app for VYOMAA LABS' DPIIT filing.

---

I'm building the GUI for "PocketMind" — a demo Android app (runs as a local
web page in Chrome, served from a Python process in Termux, 100% offline,
no cloud calls ever) that bundles three separate on-device AI tools. This
is going in a hackathon demo video and in front of investors, so it needs
to look genuinely polished and distinct per tool — not one reskinned theme
repeated three times with different labels.

**The three tools, and the visual identity each one needs:**

1. **AgriLens** — a farmer photographs a crop leaf (chilli/tomato/maize),
   an on-device image classifier IDs the disease, and a small language
   model explains it in plain language. Visual identity: organic,
   earthy, grounded — this one can lean into natural/plant motifs (leaf
   shapes, soil tones, a "scan frame" around the photo upload).
2. **LearnLoop** — a student types a Class 8-10 Maths/Science/Social
   question, the app matches it to verified textbook content and a
   small model explains it like a patient tutor. Visual identity:
   academic, calm, legible — think a well-designed study app or a nice
   notebook, not the same leaf/soil palette as AgriLens. Should feel
   distinct from AgriLens even though it shares the same page shell.
3. **Fleet Risk** — replays a real recorded vehicle trip (accelerometer +
   gyroscope stream, the same signal an ESP32 + IMU rig mounted near a
   car's OBD2 port would produce) through an on-device two-stage
   RandomForest model, which flags moments of elevated accident risk and
   explains *why* (which driving behavior it thinks it detected: sudden
   braking, sudden acceleration, a sharp lane change, etc.). Visual
   identity: this one should look like a **real telemetry/dashboard
   view** — a bar chart of risk-tier counts (low/medium/high), a
   timeline strip showing risk level over the course of the trip, and a
   list of flagged moments styled as highlighted event cards (timestamp,
   risk tier, confidence, and the "likely behavior" reasoning) — NOT a
   wall of monospace text. This is the one place in the whole app that
   should look like a dashboard instead of a form.

All three share one page shell (a header with the "PocketMind" wordmark
and a small "100% on-device / no cloud" badge, plus a 4-way nav: Home,
AgriLens, LearnLoop, Fleet Risk) but each tool's own content area should
read as its own distinct environment within that shared shell — like three
well-designed sections of one product, not one template with swapped text.

**Hard technical constraints (don't break these):**

- Output plain HTML + CSS + vanilla JS only. No build step, no React/Vue,
  no npm. This gets pasted into Python string literals and served as-is
  by a stdlib `http.server` — nothing compiles it.
- **No external CDN scripts or stylesheets of any kind — including chart
  libraries (no Chart.js, no D3, nothing from a CDN).** The entire point
  of this demo is that it works with the phone in airplane mode. A chart
  library loaded from a CDN would silently break (or worse, silently
  degrade) the one claim this demo exists to prove. Draw the Fleet Risk
  bar chart and timeline with plain CSS (div widths/heights as bars) or
  inline SVG you generate in JS from the JSON data below. Fonts: if you
  want custom fonts, either inline a `@font-face` with a data URI, or
  stick to system fonts — same CDN restriction applies to Google Fonts
  (it's loaded with a `<link>` currently, which does hit a network
  request on first load; flag this to me as a tradeoff if you keep it
  rather than silently deciding).
- Forms submit via `fetch()`, not a real page navigation, so the page can
  show a live state while waiting. **AgriLens and LearnLoop calls take
  15-85 real seconds** (an on-device language model is actually running —
  show a live elapsed-time counter, not a fake spinner, so it reads as
  honest rather than broken). **Fleet Risk replies in under 300ms** (it's
  a small decision-tree walk, not a language model) — don't put a long
  "thinking" animation on it, a brief instant transition is more honest
  and more impressive.
- Multipart vs. urlencoded matters: AgriLens's form has a file input and
  must submit as `multipart/form-data` (plain `fetch(url, {body: new
  FormData(form)})` already does this correctly). LearnLoop and Fleet
  Risk have no file input and must submit as
  `application/x-www-form-urlencoded` — `fetch` does NOT do this
  automatically for a FormData body, so you need:
  ```js
  body: new URLSearchParams(new FormData(form)).toString()
  // with header 'Content-Type': 'application/x-www-form-urlencoded'
  ```
  Keep this branch (file input present → FormData; absent → urlencoded)
  if you restructure the JS — this exact bug broke LearnLoop once before.
- Every fetch POST must send the header `X-Requested-With: fetch` — the
  server uses this to decide whether to return JSON (fetch path) or a
  full HTML page (plain-form fallback with JS disabled). Keep that
  header on every submit.
- Escape all server-returned text before inserting into the DOM (it's
  model output / user input — never use raw string concatenation into
  innerHTML without escaping).

**The exact JSON each endpoint returns on a `fetch` POST** (design your
result UI around these real shapes — don't invent fields that aren't
here):

`POST /agrilens` and `POST /learnloop` both return either:
```json
{"title": "string", "meta": "string (classifier info / match info + timing)",
 "answer": "string (the plain-language explanation, can be multi-sentence)",
 "caveat": "string (one line, e.g. 'confirm with your KVK')}
```
or on error: `{"error": "string"}`

`POST /fleet` returns:
```json
{
  "title": "string (trip name)",
  "meta": "string (which trip, model info, replay time in ms)",
  "answer": "string (plain-text fallback log, you don't need to show this verbatim if you build the chart/event-card UI instead)",
  "caveat": "string (the 'behavior classifier, not a crash predictor' disclaimer -- must stay visible somewhere, it's a legal/honesty requirement, not decoration)",
  "chart": {
    "n_rows": 1034,
    "n_events": 246,
    "tier_counts": {"low": 788, "medium": 31, "high": 215},
    "timeline": [{"t": 0.0, "tier": "low", "p": 0.055}, "... ~120 points across the trip, t in seconds, tier is low/medium/high, p is the model's risk probability 0-1 ..."]
  },
  "events": [
    {"t": 2.26, "tier": "high", "p": 0.526,
     "behaviors": [["sudden-acc", 0.319], ["sudden-right-line-chg", 0.2]]},
    "... up to 40 events, each behaviors list is the model's top-2 guesses at WHAT kind of driving event this was, with confidence -- this IS the reasoning, surface it clearly, e.g. 'likely sudden acceleration (32%)' ..."
  ],
  "events_truncated": 206
}
```
or on error: `{"error": "string"}`

Build the Fleet Risk result view from `chart` and `events`, not from
parsing `answer`. A good shape: a 3-bar chart for tier_counts (low/medium/
high, sized by count, colored by severity), a thin horizontal timeline
strip below it (could be a row of small colored ticks/segments from the
`timeline` array, colored by tier, so the whole trip's risk profile reads
at a glance), then a scrollable list of event cards for the worst few
`events` (sorted by `p` descending is fine even though the API returns
them chronological) each showing: timestamp, a tier badge (color-coded
low/medium/high), the probability, and the top reasoning behavior
formatted as something like "Likely: sudden braking (32%)".

**Here is the exact current `app.py`** — the full backend, so you can see
every route, every page function, and the current (functional but
visually plain) HTML/CSS it generates. Keep the Python structure and
function names; I only need new values for `PAGE_HEAD`'s `<style>` block,
the body markup each `*_form()` / `result_card()` function returns, and
`PAGE_SCRIPT`'s JS (which you'll need to extend for the Fleet Risk chart
rendering, since the current JS just dumps `answer` into a `<pre>`):

```python
"""PocketMind demo server — AgriLens + LearnLoop, one process, Termux-ready.

stdlib-only web server (http.server) serving two tools against one shared
engine (llama-server + the advice/content banks). This is deliberately the
"fastest build path" the project's own PROOF_AND_PILOT_PLAN.md calls for:
a local web page on the phone's own localhost, opened in the phone's
browser, no native app. It's labeled a prototype everywhere it matters.

The UI submits via fetch() so it can show a live "thinking" timer instead of
a frozen page — on-device generation genuinely takes 40-90s on a phone this
old (measured, not guessed), so pretending otherwise would just look broken.
A plain <form> POST still works with JS disabled; the server tells the two
paths apart with the X-Requested-With header and returns JSON for the fetch
path, a full page otherwise.

Run: python3 app.py   (serves http://127.0.0.1:8090)
Requires: llama-server already running on :8080 (engine/setup_termux.sh),
and AgriLens's classify.py + its .npz weights present (agrilens/).
"""
from __future__ import annotations

import html
import json
import sys
import tempfile
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ENGINE_DIR = Path(__file__).parent
ROOT_DIR = ENGINE_DIR.parent
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(ROOT_DIR / "agrilens"))
sys.path.insert(0, str(ROOT_DIR / "vehicle-risk"))

from retrieval import Retriever  # noqa: E402
from llama_client import LlamaClient, build_prompt, LlamaServerError  # noqa: E402
from infer import RiskModel, format_text, replay_trip_struct  # noqa: E402

ADVICE_BANK = Retriever(sorted((ROOT_DIR / "advice_bank").glob("*.md")))
LEARN_CONTENT = Retriever(sorted((ROOT_DIR / "learnloop").glob("content_*.md")))
LLAMA = LlamaClient()
RISK_MODEL = RiskModel()
SAMPLE_TRIPS_DIR = ROOT_DIR / "vehicle-risk" / "data" / "sample_trips"

CAVEAT_AGRI = "Advice only. Confirm with your agriculture officer / KVK before acting."
CAVEAT_LEARN = "Practice answer from LearnLoop — a prototype tutor. Confirm with your teacher."
CAVEAT_FLEET = ("Behavior classifier, not a crash predictor — no public dataset pairs raw "
                "telemetry with real crash outcomes. Runs entirely on-device, same model "
                "size an ESP32 firmware port would use.")

PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PocketMind — VYOMAA LABS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..600&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #f6f1e6;
    --paper-card: #fffcf6;
    --ink: #2b2420;
    --ink-soft: #7a6e60;
    --line: #e4d8c3;
    --sage: #7c8a6a;
    --sage-ink: #35401f;
    --clay: #bd6f45;
    --clay-soft: #f1e0cf;
    --danger: #a8503c;
    --radius-lg: 22px;
    --radius-md: 14px;
    --radius-sm: 10px;
  }

  *, *::before, *::after { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

  html, body { height: 100%; }

  body {
    background: var(--paper);
    color: var(--ink);
    font-family: 'Source Sans 3', system-ui, -apple-system, sans-serif;
    margin: 0;
    padding: 28px 18px 48px;
    max-width: 480px;
    margin-inline: auto;
    line-height: 1.55;
  }

  header {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 26px;
  }

  .brand-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }

  h1 {
    font-family: 'Fraunces', Georgia, serif;
    font-optical-sizing: auto;
    font-style: italic;
    font-size: 2rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.01em;
    color: var(--ink);
  }

  .offline-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    color: var(--clay);
    font-size: 0.68rem;
    font-weight: 600;
    padding: 4px 0;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .offline-badge::before {
    content: '';
    width: 6px;
    height: 6px;
    background-color: var(--clay);
    border-radius: 50%;
    flex: none;
  }

  .sub {
    color: var(--ink-soft);
    font-size: 0.88rem;
    margin: 0;
    font-weight: 400;
    border-top: 1px solid var(--line);
    padding-top: 12px;
  }

  nav {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
    margin-bottom: 26px;
  }

  nav a {
    text-align: center;
    color: var(--ink-soft);
    text-decoration: none;
    padding: 10px 8px;
    border-radius: var(--radius-sm);
    font-size: 0.82rem;
    font-weight: 600;
    border: 1px solid var(--line);
    transition: all 0.2s ease;
  }

  nav a:hover {
    border-color: var(--sage);
    color: var(--ink);
  }

  nav a.active {
    background: var(--sage);
    color: #fdfbf4;
    border-color: var(--sage);
  }

  .card {
    background: var(--paper-card);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 2px rgba(43, 36, 32, 0.04);
  }

  .card h3 {
    font-family: 'Fraunces', Georgia, serif;
    font-weight: 600;
    font-size: 1.2rem;
  }

  label {
    display: block;
    font-size: 0.72rem;
    color: var(--ink-soft);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
  }

  input[type=file], input[type=text], select {
    width: 100%;
    background: var(--paper);
    color: var(--ink);
    border: 1.5px solid var(--line);
    border-radius: var(--radius-sm);
    padding: 13px 14px;
    font-size: 0.95rem;
    font-family: inherit;
    margin-bottom: 16px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  input[type=file]::file-selector-button {
    background: var(--clay-soft);
    color: var(--clay);
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    font-weight: 600;
    margin-right: 12px;
    cursor: pointer;
  }

  input[type=text]:focus, input[type=file]:focus, select:focus {
    outline: none;
    border-color: var(--sage);
    box-shadow: 0 0 0 3px rgba(124, 138, 106, 0.18);
  }

  button[type=submit], .btn-action {
    background: var(--sage);
    color: #fdfbf4;
    border: none;
    border-radius: var(--radius-sm);
    padding: 14px 20px;
    font-weight: 600;
    font-size: 0.95rem;
    font-family: inherit;
    cursor: pointer;
    width: 100%;
    text-decoration: none;
    box-sizing: border-box;
    transition: background 0.2s, transform 0.1s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  button[type=submit]:hover, .btn-action:hover { background: var(--sage-ink); }
  button[type=submit]:active, .btn-action:active { transform: scale(0.98); }

  button[type=submit]:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .result {
    border-left: 3px solid var(--clay);
    animation: riseIn 0.35s ease;
  }

  @keyframes riseIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: none; }
  }

  .result h3 {
    margin: 0 0 8px;
    color: var(--ink);
  }

  .meta {
    color: var(--ink-soft);
    font-size: 0.74rem;
    margin-bottom: 14px;
    font-weight: 500;
    background: var(--clay-soft);
    padding: 5px 10px;
    border-radius: 6px;
    display: inline-block;
  }

  .caveat {
    margin-top: 16px;
    font-size: 0.78rem;
    color: var(--ink-soft);
    border-top: 1px solid var(--line);
    padding-top: 12px;
    line-height: 1.45;
  }

  .err {
    color: var(--danger);
    font-weight: 600;
    margin: 0;
  }

  pre {
    white-space: pre-wrap;
    font-family: inherit;
    line-height: 1.6;
    margin: 0;
    font-size: 0.925rem;
    color: var(--ink);
  }

  .thinking {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--clay);
    font-size: 0.9rem;
    font-weight: 600;
  }

  .spinner {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 2.5px solid var(--clay-soft);
    border-top-color: var(--clay);
    animation: spin 0.8s linear infinite;
    flex: none;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .thinking .t { font-variant-numeric: tabular-nums; }

  .hint {
    font-size: 0.75rem;
    color: var(--ink-soft);
    margin-top: 8px;
  }
</style></head><body>
<header>
  <div class="brand-row">
    <h1>PocketMind</h1>
    <div class="offline-badge">On-device</div>
  </div>
  <p class="sub">VYOMAA LABS — zero cloud calls, runs locally via Termux</p>
</header>
<nav>
  <a href="/" class="__NAV_HOME__">Home</a>
  <a href="/agrilens" class="__NAV_AGRI__">AgriLens</a>
  <a href="/learnloop" class="__NAV_LEARN__">LearnLoop</a>
  <a href="/fleet" class="__NAV_FLEET__">Fleet Risk</a>
</nav>
"""
PAGE_SCRIPT = """
<script>
(function(){
  function fmtT(s){ return s.toFixed(1) + "s"; }
  function escapeHtml(s){
    return s.replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
    });
  }
  function resultCard(data){
    if (data.error){
      return '<div class="card"><p class="err">' + escapeHtml(data.error) + '</p></div>';
    }
    return '<div class="card result">' +
      '<h3>' + escapeHtml(data.title) + '</h3>' +
      '<div class="meta">' + escapeHtml(data.meta) + '</div>' +
      '<pre>' + escapeHtml(data.answer) + '</pre>' +
      '<div class="caveat">' + escapeHtml(data.caveat) + '</div>' +
      '</div>';
  }
  document.querySelectorAll('form[data-pm]').forEach(function(form){
    var resultBox = document.getElementById(form.dataset.pm);
    var btn = form.querySelector('button');
    var btnLabel = btn.textContent;
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      btn.disabled = true;
      var start = Date.now();
      resultBox.innerHTML = '<div class="card">' +
        '<div class="thinking"><span class="spinner"></span>' +
        '<span>Thinking on-device <span class="t">0.0s</span></span></div>' +
        '<div class="hint">A 1.5B model on this phone takes real time — no shortcuts, no cloud call.</div>' +
        '</div>';
      var timerEl = resultBox.querySelector('.t');
      var timer = setInterval(function(){
        timerEl.textContent = fmtT((Date.now() - start) / 1000);
      }, 100);
      var hasFile = form.querySelector('input[type=file]');
      var opts;
      if (hasFile){
        opts = {method:'POST', headers:{'X-Requested-With':'fetch'}, body:new FormData(form)};
      } else {
        opts = {method:'POST',
          headers:{'X-Requested-With':'fetch','Content-Type':'application/x-www-form-urlencoded'},
          body:new URLSearchParams(new FormData(form)).toString()};
      }
      fetch(form.action, opts).then(function(r){ return r.json(); })
        .then(function(data){
          clearInterval(timer);
          resultBox.innerHTML = resultCard(data);
          btn.disabled = false;
          btn.textContent = btnLabel;
        }).catch(function(e){
          clearInterval(timer);
          resultBox.innerHTML = '<div class="card"><p class="err">Request failed: ' +
            escapeHtml(String(e)) + '</p></div>';
          btn.disabled = false;
          btn.textContent = btnLabel;
        });
    });
  });
})();
</script>
"""
PAGE_TAIL = "</body></html>"


def render(body: str, active: str = "") -> bytes:
    head = (PAGE_HEAD
            .replace("__NAV_HOME__", "active" if active == "home" else "")
            .replace("__NAV_AGRI__", "active" if active == "agri" else "")
            .replace("__NAV_LEARN__", "active" if active == "learn" else "")
            .replace("__NAV_FLEET__", "active" if active == "fleet" else ""))
    return (head + body + PAGE_SCRIPT + PAGE_TAIL).encode("utf-8")


def home_page() -> bytes:
    body = """
<div class="card">
  <h3 style="margin-top:0">AgriLens</h3>
  <p class="meta" style="font-family:inherit; display:block; background:none; padding:0">Point a camera at a chilli, tomato, or maize leaf. Get an offline health read.</p>
  <a href="/agrilens" class="btn-action">Open AgriLens</a>
</div>
<div class="card">
  <h3 style="margin-top:0">LearnLoop</h3>
  <p class="meta" style="font-family:inherit; display:block; background:none; padding:0">Ask a class 8-10 Maths, Science, or Social question. Get a plain-language explanation.</p>
  <a href="/learnloop" class="btn-action">Open LearnLoop</a>
</div>
<div class="card">
  <h3 style="margin-top:0">Fleet Risk</h3>
  <p class="meta" style="font-family:inherit; display:block; background:none; padding:0">Replay a real recorded trip's accelerometer/gyro stream through the on-device risk model, same as an ESP32+IMU rig would send.</p>
  <a href="/fleet" class="btn-action">Open Fleet Risk</a>
</div>
"""
    return render(body, "home")


def agrilens_form(result_html: str = "") -> bytes:
    body = f"""
<div class="card">
  <form method="POST" action="/agrilens" enctype="multipart/form-data" data-pm="agrilens-result">
    <label>Crop photo</label>
    <input type="file" name="photo" accept="image/*" capture="environment" required>
    <button type="submit">Analyze offline</button>
  </form>
</div>
<div id="agrilens-result">{result_html}</div>
"""
    return render(body, "agri")


def learnloop_form(result_html: str = "") -> bytes:
    body = f"""
<div class="card">
  <form method="POST" action="/learnloop" data-pm="learnloop-result">
    <label>Your question (Maths / Science / Social, class 8-10)</label>
    <input type="text" name="question" placeholder="e.g. What is the Pythagoras theorem?" required>
    <button type="submit">Ask offline</button>
  </form>
</div>
<div id="learnloop-result">{result_html}</div>
"""
    return render(body, "learn")


def fleet_form(result_html: str = "") -> bytes:
    trips = sorted(p.name for p in SAMPLE_TRIPS_DIR.glob("*.csv"))
    options = "".join(f'<option value="{html.escape(t)}">{html.escape(_trip_label(t))}</option>' for t in trips)
    body = f"""
<div class="card">
  <form method="POST" action="/fleet" data-pm="fleet-result">
    <label>Recorded trip (accelerometer + gyroscope stream)</label>
    <select name="trip">{options}</select>
    <button type="submit">Replay on-device</button>
  </form>
  <p class="hint" style="margin-top:14px">Same raw IMU signal an ESP32 + MPU6050/9250 rig streams from the OBD2-adjacent sensor mount. Two-stage RandomForest, 30 trees each, no cloud call.</p>
</div>
<div id="fleet-result">{result_html}</div>
"""
    return render(body, "fleet")


def _trip_label(fname: str) -> str:
    parts = fname.replace(".csv", "").split("_")
    return " ".join(parts[1:3]) if len(parts) > 2 else fname


def result_card(title: str, meta: str, answer: str, caveat: str) -> str:
    return f"""
<div class="card result">
  <h3>{html.escape(title)}</h3>
  <div class="meta">{html.escape(meta)}</div>
  <pre>{html.escape(answer)}</pre>
  <div class="caveat">{html.escape(caveat)}</div>
</div>
"""


def error_card(msg: str) -> str:
    return f'<div class="card"><p class="err">{html.escape(msg)}</p></div>'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _is_ajax(self) -> bool:
        return self.headers.get("X-Requested-With", "") == "fetch"

    def _send(self, body: bytes, status: int = 200, content_type: str = "text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self._send(body, status, "application/json; charset=utf-8")

    def do_GET(self):
        if self.path == "/":
            self._send(home_page())
        elif self.path.startswith("/agrilens"):
            self._send(agrilens_form())
        elif self.path.startswith("/learnloop"):
            self._send(learnloop_form())
        elif self.path.startswith("/fleet"):
            self._send(fleet_form())
        else:
            self._send(b"not found", 404)

    def do_POST(self):
        try:
            if self.path.startswith("/agrilens"):
                self._handle_agrilens()
            elif self.path.startswith("/learnloop"):
                self._handle_learnloop()
            elif self.path.startswith("/fleet"):
                self._handle_fleet()
            else:
                self._send(b"not found", 404)
        except Exception as e:
            traceback.print_exc()
            if self._is_ajax():
                self._send_json({"error": f"Server error: {e}"}, 500)
            else:
                self._send(agrilens_form(error_card(f"Server error: {e}")), 500)

    # ---- AgriLens ----
    def _handle_agrilens(self):
        ajax = self._is_ajax()
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        ctype = self.headers.get("Content-Type", "")
        if "boundary=" not in ctype:
            msg = "No file received."
            self._send_json({"error": msg}, 400) if ajax else self._send(agrilens_form(error_card(msg)), 400)
            return
        boundary = ctype.split("boundary=")[-1].encode()
        image_bytes = _extract_multipart_file(raw, boundary, field_name=b"photo")
        if not image_bytes:
            msg = "Couldn't read the uploaded photo."
            self._send_json({"error": msg}, 400) if ajax else self._send(agrilens_form(error_card(msg)), 400)
            return

        t0 = time.time()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            tf.write(image_bytes)
            tmp_path = tf.name

        try:
            from classify import classify  # agrilens/classify.py, see NOTES.md
        except ImportError as e:
            msg = f"AgriLens classifier not installed yet ({e}). Run the setup in agrilens/ first."
            self._send_json({"error": msg}, 500) if ajax else self._send(agrilens_form(error_card(msg)), 500)
            return

        cls_result = classify(tmp_path)
        label = cls_result["class_name"]
        chunk = ADVICE_BANK.by_classifier_label(label)
        classify_ms = int((time.time() - t0) * 1000)

        if chunk is None:
            answer = (f"Classifier result: {label} (confidence {cls_result['confidence']:.0%}). "
                      f"No advice-bank entry for this exact class yet.")
            llm_ms = 0
        else:
            prompt = build_prompt(
                system=("You are AgriLens, an offline farm-advisory assistant. Explain the "
                        "following verified agronomy note in plain, simple language for a "
                        "farmer. Do not add any fact, chemical name, or dose that isn't in "
                        "the note below."),
                user=f"Classifier diagnosis: {chunk.title}\n\nVerified note:\n{chunk.body}\n\n"
                     f"Explain this in 3-4 short sentences.",
            )
            t1 = time.time()
            answer = LLAMA.complete(prompt, max_tokens=220)
            llm_ms = int((time.time() - t1) * 1000)

        title = chunk.title if chunk else label
        meta = (f"Classifier: {label} · confidence {cls_result['confidence']:.0%} · "
                f"classify {classify_ms}ms · SLM {llm_ms}ms · fully offline")
        if ajax:
            self._send_json({"title": title, "meta": meta, "answer": answer, "caveat": CAVEAT_AGRI})
        else:
            self._send(agrilens_form(result_card(title, meta, answer, CAVEAT_AGRI)))

    # ---- LearnLoop ----
    def _handle_learnloop(self):
        ajax = self._is_ajax()
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        fields = parse_qs(raw)
        question = (fields.get("question") or [""])[0].strip()
        if not question:
            msg = "Type a question first."
            self._send_json({"error": msg}, 400) if ajax else self._send(learnloop_form(error_card(msg)), 400)
            return

        hits = LEARN_CONTENT.search(question, top_k=1)
        t0 = time.time()
        if not hits:
            answer = ("I don't have a verified note on that topic yet in this prototype's "
                       "content pack — try a Class 8-10 Maths, Science, or Social question "
                       "close to the sample topics (e.g. Pythagoras theorem, photosynthesis, "
                       "fundamental rights).")
            meta = "No matching content-pack entry · fully offline"
            title = "No match"
        else:
            chunk = hits[0]
            prompt = build_prompt(
                system=("You are LearnLoop, an offline study partner for an Indian school "
                        "student. Explain the following verified note in plain language, "
                        "like a patient tutor. Do not add any fact that isn't in the note."),
                user=f"Student's question: {question}\n\nVerified note ({chunk.title}):\n"
                     f"{chunk.body}\n\nExplain it, and if useful, walk through the example step by step.",
            )
            answer = LLAMA.complete(prompt, max_tokens=400)
            meta = (f"Matched: {chunk.title} ({chunk.fields.get('class', '?')} "
                    f"{chunk.fields.get('subject', '')}) · {int((time.time()-t0)*1000)}ms · fully offline")
            title = chunk.title

        if ajax:
            self._send_json({"title": title, "meta": meta, "answer": answer, "caveat": CAVEAT_LEARN})
        else:
            self._send(learnloop_form(result_card(title, meta, answer, CAVEAT_LEARN)))

    # ---- Fleet Risk ----
    def _handle_fleet(self):
        ajax = self._is_ajax()
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        fields = parse_qs(raw)
        trip = (fields.get("trip") or [""])[0].strip()
        trip_path = SAMPLE_TRIPS_DIR / trip
        if not trip or not trip_path.is_file():
            msg = "Pick a recorded trip first."
            self._send_json({"error": msg}, 400) if ajax else self._send(fleet_form(error_card(msg)), 400)
            return

        t0 = time.time()
        struct = replay_trip_struct(RISK_MODEL, trip_path)
        ms = int((time.time() - t0) * 1000)
        title = _trip_label(trip)
        meta = f"Replayed {trip} · 2-stage RandomForest (60 trees total) · {ms}ms · fully offline"

        if ajax:
            # chart/events: structured data for a frontend to actually plot
            # (tier bar counts, a risk-over-time timeline, ranked event cards
            # with the reasoning) instead of parsing the text log.
            self._send_json({
                "title": title, "meta": meta, "caveat": CAVEAT_FLEET,
                "answer": format_text(struct),  # text fallback
                "chart": {
                    "n_rows": struct["n_rows"],
                    "n_events": struct["n_events"],
                    "tier_counts": struct["tier_counts"],
                    "timeline": struct["timeline"],
                },
                "events": struct["events"],
                "events_truncated": struct["events_truncated"],
            })
        else:
            self._send(fleet_form(result_card(title, meta, format_text(struct), CAVEAT_FLEET)))


def _extract_multipart_file(raw: bytes, boundary: bytes, field_name: bytes) -> bytes | None:
    """Minimal multipart/form-data parser for a single file field.

    Avoids the `cgi` module on purpose (deprecated/removed in newer Python,
    and Termux's Python version shouldn't be a gamble for something this
    small to hand-roll).
    """
    parts = raw.split(b"--" + boundary)
    for part in parts:
        if (b'name="' + field_name + b'"') not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        body = part[header_end + 4:]
        if body.endswith(b"\r\n"):
            body = body[:-2]
        return body
    return None


def main():
    port = 8090
    print(f"PocketMind demo server on http://127.0.0.1:{port}")
    print(f"advice bank: {len(ADVICE_BANK.chunks)} chunks | learnloop: {len(LEARN_CONTENT.chunks)} chunks")
    print(f"llama-server reachable: {LLAMA.health()}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
```

**What I need back from you:**

1. The new `<style>` block contents (can reuse CSS custom properties /
   tokens across all three tools' sub-themes, redefined per active page
   if that's how you choose to differentiate them — e.g. a `body[data-tool=fleet]`
   selector, or distinct classes on each page's root container).
2. The new body markup for `home_page()`, `agrilens_form()`,
   `learnloop_form()`, `fleet_form()`, and `result_card()` (note:
   `result_card()` is currently generic/shared across all three tools —
   tell me if you want it to stay one function with tool-specific CSS
   classes, or if Fleet Risk's result should be built by different JS
   entirely since it needs the chart, not just text).
3. The updated `PAGE_SCRIPT` JS — specifically the part that builds the
   Fleet Risk result view from the `chart`/`events` JSON (the current JS
   only knows how to render `{title, meta, answer, caveat}` into a
   `<pre>` block; it needs a second code path for Fleet Risk's richer
   response).
4. Any new container IDs/classes you introduce, so I know what to wire up
   on the Python side with zero guessing.

Keep everything mobile-width (phone browser, ~360-420px). Keep the file
count at one page — no separate CSS/JS files, this all lives in Python
string literals that get concatenated and served inline.
