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

# Stress-test derived (2026-10-15): correct lab-photo classifications land
# at 94-100% confidence; both real-world misclassifications and non-leaf
# garbage input (tested: a photo of paper) land at 38-68%. See
# BATTLE_TEST_REPORT.md.
AGRI_CONFIDENCE_FLOOR = 0.70

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
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..600&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #f7f3ee;
    --paper-card: #ffffff;
    --ink: #1f1b18;
    --ink-soft: #635952;
    --line: #e6dfd5;
    --accent: #4a6741;
    --accent-soft: #eaf2e8;
    --clay: #a65d37;
    --danger: #b33f32;
    --radius-xl: 28px;
    --radius-lg: 20px;
    --radius-sm: 12px;
  }

  *, *::before, *::after { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; }

  body {
    background: var(--paper);
    color: var(--ink);
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 24px 16px 48px;
    max-width: 440px;
    margin-inline: auto;
    line-height: 1.5;
    transition: background 0.3s ease, color 0.3s ease;
  }

  header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 20px;
  }

  .brand-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  h1 {
    font-family: 'Fraunces', Georgia, serif;
    font-style: italic;
    font-size: 1.8rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.02em;
    color: var(--ink);
  }

  .offline-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.7rem;
    font-weight: 700;
    padding: 6px 12px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  .offline-badge::before {
    content: '';
    width: 6px;
    height: 6px;
    background-color: var(--accent);
    border-radius: 50%;
  }

  .sub {
    color: var(--ink-soft);
    font-size: 0.82rem;
    margin: 0;
    font-weight: 400;
  }

  nav {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 24px;
    background: var(--line);
    padding: 4px;
    border-radius: 24px;
  }

  nav a {
    text-align: center;
    color: var(--ink-soft);
    text-decoration: none;
    padding: 10px 4px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  nav a:hover { color: var(--ink); }
  nav a.active {
    background: var(--paper-card);
    color: var(--accent);
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }

  .card {
    background: var(--paper-card);
    border: 1px solid var(--line);
    border-radius: var(--radius-xl);
    padding: 22px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 8px 24px rgba(0, 0, 0, 0.01);
  }

  .card h3 {
    font-family: 'Fraunces', Georgia, serif;
    font-weight: 600;
    font-size: 1.2rem;
    margin-top: 0;
    margin-bottom: 12px;
  }

  label {
    display: block;
    font-size: 0.74rem;
    color: var(--ink-soft);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
  }

  input[type=file], input[type=text], select {
    width: 100%;
    background: var(--paper);
    color: var(--ink);
    border: 1.5px solid var(--line);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    font-size: 0.95rem;
    font-family: inherit;
    margin-bottom: 16px;
    transition: all 0.2s ease;
  }

  input[type=file]::file-selector-button {
    background: var(--accent-soft);
    color: var(--accent);
    border: none;
    padding: 8px 12px;
    border-radius: 8px;
    font-weight: 600;
    margin-right: 12px;
    cursor: pointer;
  }

  input[type=text]:focus, input[type=file]:focus, select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 4px var(--accent-soft);
    background: var(--paper-card);
  }

  button[type=submit], .btn-action {
    background: var(--accent);
    color: var(--paper-card);
    border: none;
    border-radius: 22px;
    padding: 14px 20px;
    font-weight: 600;
    font-size: 0.95rem;
    font-family: inherit;
    cursor: pointer;
    width: 100%;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.15s ease;
    box-shadow: 0 4px 12px var(--accent-soft);
  }

  button[type=submit]:hover, .btn-action:hover { opacity: 0.92; }
  button[type=submit]:active, .btn-action:active { transform: scale(0.98); }
  button[type=submit]:disabled { opacity: 0.4; cursor: default; box-shadow: none; }

  .result {
    border-left: 4px solid var(--accent);
    animation: fadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: none; }
  }

  .meta {
    color: var(--accent);
    font-size: 0.75rem;
    margin-bottom: 14px;
    font-weight: 600;
    background: var(--accent-soft);
    padding: 6px 10px;
    border-radius: 8px;
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

  .err { color: var(--danger); font-weight: 600; margin: 0; }
  pre { white-space: pre-wrap; font-family: inherit; line-height: 1.6; margin: 0; font-size: 0.925rem; }

  .thinking {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--accent);
    font-size: 0.9rem;
    font-weight: 600;
  }

  .spinner {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 2.5px solid var(--accent-soft);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
    flex: none;
  }

  @keyframes spin { to { transform: rotate(360deg); } }
  .thinking .t { font-variant-numeric: tabular-nums; }
  .hint { font-size: 0.76rem; color: var(--ink-soft); margin-top: 8px; }

  /* Fleet Dashboard UI Elements */
  .fleet-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }
  .stat-box {
    background: var(--paper);
    border: 1px solid var(--line);
    padding: 10px 8px;
    border-radius: var(--radius-sm);
    text-align: center;
  }
  .stat-box .val { font-size: 1.2rem; font-weight: 700; color: var(--ink); }
  .stat-box.low .val { color: var(--accent); }
  .stat-box.med .val { color: var(--clay); }
  .stat-box.high .val { color: var(--danger); }
  .stat-box .lbl { font-size: 0.65rem; text-transform: uppercase; color: var(--ink-soft); font-weight: 700; margin-top: 2px; }

  .timeline-bar {
    height: 16px;
    width: 100%;
    background: var(--paper);
    border-radius: 8px;
    display: flex;
    overflow: hidden;
    margin: 10px 0 18px;
    border: 1px solid var(--line);
  }
  .timeline-seg { height: 100%; flex: 1; }

  .event-list { display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; padding-right: 2px; }
  .event-card {
    background: var(--paper);
    border: 1px solid var(--line);
    padding: 12px 14px;
    border-radius: var(--radius-sm);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
  }
  .event-info { display: flex; flex-direction: column; gap: 3px; }
  .event-time { font-size: 0.72rem; color: var(--ink-soft); font-weight: 700; }
  .event-desc { font-size: 0.86rem; font-weight: 600; color: var(--ink); }
  .badge {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    padding: 4px 8px;
    border-radius: 6px;
    white-space: nowrap;
  }
  .badge.low { background: var(--accent-soft); color: var(--accent); }
  .badge.medium { background: rgba(166, 93, 55, 0.12); color: var(--clay); }
  .badge.high { background: rgba(179, 63, 50, 0.12); color: var(--danger); }
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

  function renderFleetResult(data) {
    if (data.error) {
      return '<div class="card"><p class="err">' + escapeHtml(data.error) + '</p></div>';
    }

    var counts = data.chart.tier_counts || {low: 0, medium: 0, high: 0};
    var timeline = data.chart.timeline || [];
    var events = data.events || [];

    var timelineHtml = '';
    if (timeline.length > 0) {
      timelineHtml = '<div class="timeline-bar">';
      timeline.forEach(function(pt) {
        var col = pt.tier === 'high' ? 'var(--danger)' : (pt.tier === 'medium' ? 'var(--clay)' : 'var(--accent)');
        timelineHtml += '<div class="timeline-seg" style="background:' + col + ';" title="t=' + pt.t + 's (' + pt.tier + ')"></div>';
      });
      timelineHtml += '</div>';
    }

    var eventsHtml = '';
    if (events.length > 0) {
      var sortedEvents = events.slice().sort(function(a, b) {
        return b.p - a.p;
      }).slice(0, 15);

      sortedEvents.forEach(function(ev) {
        var topBehav = (ev.behaviors && ev.behaviors.length > 0) ? ev.behaviors[0] : ['unknown', 0];
        var behavName = topBehav[0].replace(/-/g, ' ');
        var conf = Math.round(topBehav[1] * 100);
        eventsHtml += '<div class="event-card">' +
          '<div class="event-info">' +
            '<span class="event-time">t = ' + ev.t.toFixed(2) + 's</span>' +
            '<span class="event-desc">Likely: ' + escapeHtml(behavName) + ' (' + conf + '%)</span>' +
          '</div>' +
          '<span class="badge ' + escapeHtml(ev.tier) + '">' + escapeHtml(ev.tier) + '</span>' +
        '</div>';
      });
    } else {
      eventsHtml = '<p class="hint">No high-risk events flagged in this trip segment.</p>';
    }

    return '<div class="card result">' +
      '<h3>' + escapeHtml(data.title) + '</h3>' +
      '<div class="meta">' + escapeHtml(data.meta) + '</div>' +
      '<div class="fleet-stats">' +
        '<div class="stat-box low"><div class="val">' + counts.low + '</div><div class="lbl">Low Risk</div></div>' +
        '<div class="stat-box med"><div class="val">' + counts.medium + '</div><div class="lbl">Med Risk</div></div>' +
        '<div class="stat-box high"><div class="val">' + counts.high + '</div><div class="lbl">High Risk</div></div>' +
      '</div>' +
      '<label>Trip Risk Timeline (' + data.chart.n_rows + ' data rows)</label>' +
      timelineHtml +
      '<label>Flagged Events (' + events.length + ' total)</label>' +
      '<div class="event-list">' + eventsHtml + '</div>' +
      '<div class="caveat">' + escapeHtml(data.caveat) + '</div>' +
    '</div>';
  }

  function resultCard(data, isFleet){
    if (data.error){
      return '<div class="card"><p class="err">' + escapeHtml(data.error) + '</p></div>';
    }
    if (isFleet) {
      return renderFleetResult(data);
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
    var isFleet = form.action.includes('/fleet');

    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      btn.disabled = true;
      var start = Date.now();

      if (isFleet) {
        resultBox.innerHTML = '<div class="card"><div class="thinking"><span class="spinner"></span><span>Replaying telemetry stream...</span></div></div>';
      } else {
        resultBox.innerHTML = '<div class="card">' +
          '<div class="thinking"><span class="spinner"></span>' +
          '<span>Thinking on-device <span class="t">0.0s</span></span></div>' +
          '<div class="hint">A 1.5B model on this phone takes real time — no shortcuts, no cloud call.</div>' +
          '</div>';
      }

      var timerEl = resultBox.querySelector('.t');
      var timer = null;
      if (timerEl) {
        timer = setInterval(function(){
          timerEl.textContent = fmtT((Date.now() - start) / 1000);
        }, 100);
      }

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
          if (timer) clearInterval(timer);
          resultBox.innerHTML = resultCard(data, isFleet);
          btn.disabled = false;
          btn.textContent = btnLabel;
        }).catch(function(e){
          if (timer) clearInterval(timer);
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
    <label>Crop photo (chilli / tomato / maize)</label>
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
    <label>Your question (Maths / Science / Social)</label>
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
    <label>Recorded trip telemetry</label>
    <select name="trip">{options}</select>
    <button type="submit">Replay on-device</button>
  </form>
  <p class="hint">Two-stage RandomForest model running locally via Python inference.</p>
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
        confidence = cls_result["confidence"]
        classify_ms = int((time.time() - t0) * 1000)

        # Found via stress-testing: the classifier is closed-set softmax --
        # it has no "not a leaf" option, so literally any photo (a photo of
        # paper, in one real test) gets forced into one of its ~38 disease
        # classes. Stress-test data: correct lab-photo IDs land at 94-100%
        # confidence; real-world misclassifications and non-leaf garbage
        # both land at 38-68%. Below AGRI_CONFIDENCE_FLOOR, refuse to
        # "diagnose" rather than assert a guess as if it were reliable.
        if confidence < AGRI_CONFIDENCE_FLOOR:
            title = "Not confident enough to diagnose"
            meta = f"Closest guess: {label} · confidence {confidence:.0%} · classify {classify_ms}ms · fully offline"
            answer = (f"The classifier's closest guess is \"{label}\" but at only {confidence:.0%} "
                      f"confidence, which is too low to trust. This usually means the photo isn't a "
                      f"single clear leaf (wrong subject, too blurry, too far away, bad light), or "
                      f"it's a real condition this prototype wasn't trained to recognize. Retake with "
                      f"one leaf filling the frame in good daylight, or try again.")
            if ajax:
                self._send_json({"title": title, "meta": meta, "answer": answer, "caveat": CAVEAT_AGRI})
            else:
                self._send(agrilens_form(result_card(title, meta, answer, CAVEAT_AGRI)))
            return

        chunk = ADVICE_BANK.by_classifier_label(label)

        if chunk is None:
            answer = (f"Classifier result: {label} (confidence {confidence:.0%}). "
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
        meta = (f"Classifier: {label} · confidence {confidence:.0%} · "
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
