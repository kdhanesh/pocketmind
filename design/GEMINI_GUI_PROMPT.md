# Prompt to paste into Gemini — copy everything below the line

---

I'm building "PocketMind," an on-device AI demo for an Indian startup
(VYOMAA LABS) that is being used as proof for a government (DPIIT)
startup filing and for investor demos. It runs **100% offline** on an
Android phone — no cloud, no internet — via a small local language model
(Qwen2.5, served by llama.cpp's `llama-server`) and a tiny Python web
server (stdlib `http.server`, no framework) that the phone's own browser
opens at `http://127.0.0.1:8090`.

It has two tools:
1. **AgriLens** — photograph a crop leaf, get an offline disease diagnosis
   + plain-language advice.
2. **LearnLoop** — type a Class 8-10 school question (Maths/Science/Social),
   get an offline, plain-language tutor explanation.

**I need you to redesign the GUI.** My own hand-rolled CSS wasn't good
enough — I want something that actually looks professional and polished,
with a genuine **organic / nature-inspired visual identity** (this is a
farm/agriculture + rural-education product), good typography, and real
interactivity — not a template that looks like a generic form.

## Hard requirements (don't break these — the Python backend depends on them)

The backend is fixed; you're only producing the **HTML + CSS + JS**, which
I will slot back into Python string templates. Please give me:

1. A **shared page shell** (head/nav/style) used by all 3 pages (Home,
   AgriLens, LearnLoop).
2. Each page's **body markup**.
3. **One shared `<script>` block** (vanilla JS, no framework/build step —
   this is served by a stdlib Python server on a phone with no build
   tooling) implementing the interactive behavior below.

### Pages & routes (don't change these)
- `GET /` → Home, with two cards/buttons linking to `/agrilens` and `/learnloop`.
- `GET /agrilens` → a page with a `<form>` containing a single
  `<input type="file" name="photo" accept="image/*" capture="environment">`
  and a submit button, plus a result area.
- `GET /learnloop` → a page with a `<form>` containing a single
  `<input type="text" name="question">` and a submit button, plus a result area.

### Interactive behavior (must keep working)
- Forms submit via `fetch()`, **not** a page reload (preventDefault on submit).
- The AgriLens form sends `multipart/form-data` (it has a file). The
  LearnLoop form sends `application/x-www-form-urlencoded` body built from
  its FormData (it's text-only) — **this distinction matters, mixing it up
  breaks the backend's parsing**, so keep two code paths in the submit
  handler, picked by whether the form has a file input.
- Both requests must send header `X-Requested-With: fetch` (the backend
  uses this to decide JSON vs full-page response).
- On submit: disable the button, show a "thinking" state with a spinner
  **and a live elapsed-time counter** (e.g. "Thinking on-device 12.3s") —
  **real responses take 15-85 seconds on this phone**, so a frozen page or
  a fake fast spinner would look broken/dishonest in a live demo. The
  counter must keep ticking for the full wait, not just show a static label.
- On success, the server returns JSON: `{title, meta, answer, caveat}`.
  Render it as a result card: title (heading), meta (small, e.g.
  "Classifier: X · confidence 97% · 820ms · fully offline" — a stats/benchmark
  line, make it legible, this is a selling point not an afterthought),
  answer (body text, preserve line breaks), caveat (small disclaimer text).
- On error, the server returns JSON: `{error}`. Render it as a visible
  error state (not just console.error).
- All dynamic text must be HTML-escaped before insertion (no `data.answer`
  etc. raw into innerHTML) — basic XSS hygiene.
- Keep stable container ids/selectors my Python code can target
  (`id="agrilens-result"`, `id="learnloop-result"`, or similar — just tell
  me what you used).

### Visual/UX requirements
- **Organic, nature-grounded palette** — think living plant, soil, canopy
  light, not corporate SaaS blue. Real typographic hierarchy, generous
  spacing, considered motion (subtle, not gimmicky).
- Roboto was my previous choice but **you pick the best pairing** for this
  feel if you have a better idea — just load it from Google Fonts with a
  real fallback stack (system-ui etc.), since the phone may be offline
  when the page loads (font request should fail silently, not break layout).
- **Must work well at narrow mobile width** (~360-400px) — this is a phone
  demo, held in portrait, in Chrome. No horizontal scroll, no cut-off text.
- Add a persistent, clearly visible **"100% ON-DEVICE · NO INTERNET"**
  style badge/indicator somewhere prominent (header is fine) — in the live
  demo, people must not mistake this for "just a website," so this needs
  to read as a real status indicator, not decoration.
- A small "stats strip" on the Home page would be great if you have room —
  e.g. model size, params, on-device latency range — framed as real specs,
  not marketing fluff (I'll fill in the real numbers).
- No external JS framework, no build step, no icon font — inline SVG icons
  if you want icons. Everything must be pure static HTML/CSS/JS I can paste
  into Python triple-quoted strings (so avoid backtick template literals
  with `${}` if easy to avoid — plain string concatenation in JS is fine
  and matches what's there now).

## For reference: my current (not-good-enough) implementation

Here's my current `app.py` in full — the whole page shell, both forms, the
JS, and the Python backend that serves them — so you can see the exact
contract (routes, JSON shape, container ids, encoding branching) you need
to preserve, and what the current look is so you know what to improve on:

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

from retrieval import Retriever  # noqa: E402
from llama_client import LlamaClient, build_prompt, LlamaServerError  # noqa: E402

ADVICE_BANK = Retriever(sorted((ROOT_DIR / "advice_bank").glob("*.md")))
LEARN_CONTENT = Retriever(sorted((ROOT_DIR / "learnloop").glob("content_*.md")))
LLAMA = LlamaClient()

CAVEAT_AGRI = "Advice only. Confirm with your agriculture officer / KVK before acting."
CAVEAT_LEARN = "Practice answer from LearnLoop — a prototype tutor. Confirm with your teacher."

PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PocketMind — VYOMAA LABS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#16241c; --bg2:#1f3327; --bg3:#263d2f;
    --clay:#d98a5f; --clay-dark:#1b2a21;
    --sage:#8fb996; --fern:#4f7a5c;
    --fg:#f2ede4; --muted:#a7bcac; --line:#324a3a;
    --err:#e8927a;
    --radius:16px;
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent}
  html,body{height:100%}
  body{background:
       radial-gradient(60vw 40vh at 100% -10%, rgba(143,185,150,.14), transparent 60%),
       radial-gradient(70vw 50vh at -10% 110%, rgba(217,138,95,.10), transparent 60%),
       var(--bg);
       color:var(--fg); font-family:'Roboto',system-ui,-apple-system,Segoe UI,sans-serif;
       margin:0; padding:22px 18px 40px; max-width:640px; margin-inline:auto}
  h1{font-size:1.5rem; font-weight:900; margin:0 0 4px; letter-spacing:-.01em}
  .sub{color:var(--muted); font-size:.88rem; margin-bottom:20px; line-height:1.4}
  .badge{display:inline-block; background:var(--clay); color:var(--clay-dark); font-weight:700;
         font-size:.66rem; padding:3px 9px; border-radius:20px; letter-spacing:.05em; vertical-align:2px}
  nav{display:flex; gap:8px; margin-bottom:22px}
  nav a{flex:1; text-align:center; color:var(--fg); text-decoration:none; background:var(--bg2);
        padding:11px 10px; border-radius:12px; border:1px solid var(--line); font-size:.9rem;
        font-weight:500; transition:background .15s, transform .1s, border-color .15s}
  nav a:active{transform:scale(.97)}
  nav a.active{background:var(--clay); color:var(--clay-dark); font-weight:700; border-color:var(--clay)}
  .card{background:var(--bg2); border:1px solid var(--line); border-radius:var(--radius);
        padding:20px; margin-bottom:16px; box-shadow:0 6px 20px rgba(0,0,0,.18)}
  .card h3{margin-top:0}
  label{display:block; font-size:.78rem; color:var(--sage); margin-bottom:8px;
        text-transform:uppercase; letter-spacing:.06em; font-weight:700}
  input[type=file],input[type=text],select,textarea{
    width:100%; background:var(--bg); color:var(--fg); border:1.5px solid var(--line);
    border-radius:11px; padding:12px; font-size:1rem; font-family:inherit; margin-bottom:14px;
    transition:border-color .15s}
  input[type=text]:focus{outline:none; border-color:var(--sage)}
  button{background:var(--clay); color:var(--clay-dark); border:none; border-radius:11px;
         padding:13px 20px; font-weight:700; font-size:.98rem; font-family:inherit; cursor:pointer;
         width:100%; transition:transform .1s, opacity .15s; display:flex; align-items:center;
         justify-content:center; gap:10px}
  button:active{transform:scale(.98)}
  button:disabled{opacity:.6; cursor:default}
  .result{border-left:4px solid var(--clay); padding:18px 18px 18px 16px; margin-top:4px;
          animation:riseIn .35s ease}
  @keyframes riseIn{from{opacity:0; transform:translateY(6px)} to{opacity:1; transform:none}}
  .result h3{margin:0 0 6px; font-size:1.1rem; color:var(--fg)}
  .meta{color:var(--sage); font-size:.76rem; margin-bottom:12px; font-weight:500}
  .caveat{margin-top:16px; font-size:.78rem; color:var(--muted); border-top:1px solid var(--line);
          padding-top:12px; line-height:1.4}
  .err{color:var(--err)}
  pre{white-space:pre-wrap; font-family:inherit; line-height:1.55; margin:0; font-size:.96rem}
  .thinking{display:flex; align-items:center; gap:12px; color:var(--sage); font-size:.9rem; font-weight:500}
  .spinner{width:18px; height:18px; border-radius:50%; border:2.5px solid var(--line);
           border-top-color:var(--sage); animation:spin .8s linear infinite; flex:none}
  @keyframes spin{to{transform:rotate(360deg)}}
  .thinking .t{font-variant-numeric:tabular-nums}
  .hint{font-size:.72rem; color:var(--muted); margin-top:6px}
</style></head><body>
<h1>PocketMind <span class="badge">ON-DEVICE DEMO</span></h1>
<div class="sub">VYOMAA LABS — running fully offline on this phone, no cloud call</div>
<nav>
  <a href="/" class="__NAV_HOME__">Home</a>
  <a href="/agrilens" class="__NAV_AGRI__">AgriLens</a>
  <a href="/learnloop" class="__NAV_LEARN__">LearnLoop</a>
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
            .replace("__NAV_LEARN__", "active" if active == "learn" else ""))
    return (head + body + PAGE_SCRIPT + PAGE_TAIL).encode("utf-8")


def home_page() -> bytes:
    body = """
<div class="card">
  <h3 style="margin-top:0">AgriLens</h3>
  <p class="meta" style="color:var(--muted)">Point a camera at a chilli, tomato, or maize leaf. Get an offline health read.</p>
  <a href="/agrilens"><button type="button" style="width:auto; display:inline-flex">Open AgriLens</button></a>
</div>
<div class="card">
  <h3 style="margin-top:0">LearnLoop</h3>
  <p class="meta" style="color:var(--muted)">Ask a class 8-10 Maths, Science, or Social question. Get a plain-language explanation.</p>
  <a href="/learnloop"><button type="button" style="width:auto; display:inline-flex">Open LearnLoop</button></a>
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
        else:
            self._send(b"not found", 404)

    def do_POST(self):
        try:
            if self.path.startswith("/agrilens"):
                self._handle_agrilens()
            elif self.path.startswith("/learnloop"):
                self._handle_learnloop()
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

## What I want back from you

Give me:
1. The new shared page-shell HTML/CSS (head + nav + global styles).
2. The new body markup for Home, AgriLens, and LearnLoop.
3. The new shared `<script>` block.
4. A one-line note on any container id/class names you used, if different
   from what I listed above, so I can wire them into the Python templates correctly.

---

# After Gemini replies

Paste its full reply back to me here (or save it to a file and tell me the
path) and I'll wire it into `engine/app.py`'s `PAGE_HEAD` / `PAGE_SCRIPT` /
`home_page()` / `agrilens_form()` / `learnloop_form()` / `result_card()`
functions, redeploy it to the phone, and re-screenshot the demo.
