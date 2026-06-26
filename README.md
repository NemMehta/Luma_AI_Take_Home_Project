# FlakyLens

**AI root-cause analysis for failed Playwright tests.** Upload a `trace.zip`, get back
*why* the test failed — one of four categories, a confidence score, and a reasoning
paragraph that cites the evidence it actually used.

**Live demo: https://flakylens.onrender.com**

A Playwright e2e test failing is cheap. Figuring out *why* — a renamed selector the test
owner can fix, a genuinely broken app that needs a developer now, a test that raced ahead
of the page, or a network hiccup unrelated to the code — is the expensive part, and it's a
judgment call made from messy, incomplete clues. FlakyLens makes that call: it pulls an
evidence bundle out of the trace, hands it and the failure screenshot to a vision model,
and returns a structured diagnosis that leads with its reasoning and confidence rather than
a bare verdict.

> The design rationale — why this problem, key tradeoffs, what's left out, what breaks
> first — lives in **[APPROACH.md](APPROACH.md)**. The walkthrough is in
> **[video.md](video.md)**. This README is the *what it is* and *how to run it*.

---

## Two surfaces, one repo

The single most important thing to understand about this repo: it has **two distinct
surfaces** with opposite jobs. One generates trace data offline; the other diagnoses trace
data online. They share the diagnosis code but never run together.

```
  harness/   (OFFLINE — dev-time workbench)        app/ + web/   (ONLINE — deployed webapp)
  ─────────────────────────────────────────        ──────────────────────────────────────────
  drives real Chromium via Playwright               FastAPI serves the API + the built React UI
  against the "Fruit Finder" demo app (SUT)         reads an uploaded / seeded trace.zip
  injects 4 kinds of failure                        extracts an evidence bundle (pure Python)
  emits one trace.zip per test                       + the failure screenshot  →  vision LLM
  collects a LABELED corpus + manifest              →  { category, confidence, reasoning }
  benchmarks the classifier (accuracy + matrix)     one container, one URL, port 8000, no CORS
  NEVER deployed · needs Node + browsers            NO browsers, no Playwright at runtime

                 the seam — a build-time copy, NOT a runtime dependency:

      harness/corpus/*.zip  ──►  committed snapshot  ──►  app/demo_data/
      (the harness produces the labeled data; a copy is checked in so the
       deployed app is self-contained and never imports harness/ at runtime)
```

|                    | `harness/` — offline workbench                          | `app/` + `web/` — online webapp                     |
| ------------------ | ------------------------------------------------------- | --------------------------------------------------- |
| **Job**            | *Produce & measure* — generate labeled traces, score the classifier | *Consume* — diagnose a single trace.zip      |
| **What runs**      | Node, Playwright, a real Chromium browser               | Python (FastAPI/uvicorn) + a static React bundle    |
| **Deployed?**      | No — local dev only                                     | Yes — one Docker container on Render                |
| **Browsers?**      | Yes — that's the whole point                            | No — parses the zip with `zipfile` + JSON           |
| **Input → output** | the demo app → labeled `corpus/` + `benchmark_results.json` | `trace.zip` → `{category, confidence, reasoning}` |
| **Run with**       | `npm run corpus`, `python -m harness.benchmark`         | `docker compose up --build` (or the live URL)       |

**The seam in code:** `app/main.py` points `DEMO_DATA` at `app/demo_data/`, never at
`harness/`. The four failing trace zips under `app/demo_data/traces/` are byte-identical to
`harness/corpus/*.zip`; only the manifest is reshaped (the deployed one adds a `name` field
and drops the passing baselines). So the harness is the *producer* of the corpus and the
webapp is a *self-contained consumer* of a committed snapshot.

---

## The four failure categories

Every diagnosis is exactly one of these. They're the categories the harness injects, the
labels the benchmark scores against, and the classes the model picks from.

| Category          | What it means                                                                 |
| ----------------- | ----------------------------------------------------------------------------- |
| `stale_selector`  | The selector no longer matches, but the element still exists under a changed id/text/structure. *Test owner's fix.* |
| `real_bug`        | Selectors and actions work, but the app settled into the **wrong** final state. Waiting longer would not help. *Developer's fix.* |
| `flaky_timing`    | Selectors resolve and actions run, but an assertion times out because the right state arrives **late**. Waiting would fix it. |
| `network_failure` | Failed requests, bad statuses, or missing API data are the main clue. *Often unrelated to the code.* |

> A fifth category, `race_condition`, exists in the enum (`app/diagnosis/classifier.py`)
> and the UI metadata, but it never appears in the corpus or benchmark and is not exercised.

---

## Repo layout

```
.
├── app/                      ── ONLINE: FastAPI backend (the deployed service)
│   ├── main.py               FastAPI app: API routes + serves the built React UI
│   ├── diagnosis/            trace.zip → evidence bundle → structured diagnosis
│   │   ├── ingest.py         parse the zip (pure Python) into an EvidenceBundle
│   │   ├── classifier.py     build the prompt, call the vision LLM, validate the result
│   │   └── schema.py         Pydantic models for the evidence bundle
│   ├── llm/                  one LLMClient interface over several providers
│   │   ├── factory.py        provider registry + selection (first real key wins)
│   │   ├── availability.py   live one-token ping per provider, for the model picker
│   │   ├── anthropic_client.py / openai_compatible.py / base.py
│   ├── demo_data/            committed corpus snapshot (traces + manifest + benchmark)
│   └── tests/test_evidence_guard.py
│
├── web/                      ── ONLINE: React + Vite frontend (built into the image)
│   ├── src/App.jsx           layout + shared state (selected model, corpus results)
│   ├── src/api.js            one helper per endpoint (relative, same-origin paths)
│   └── src/components/       UploadDiagnose, CorpusBrowser, Benchmark, ModelSelector, …
│
├── harness/                  ── OFFLINE: dev-time trace + benchmark workbench (not deployed)
│   ├── sut/                  the "Fruit Finder" demo app under test (NOT the product)
│   ├── server.mjs            throwaway static server for the SUT (Playwright auto-starts it)
│   ├── tests/                Playwright specs: baseline + injected pair per category
│   ├── collect-corpus.mjs    copy traces → corpus/ + write manifest.json
│   ├── benchmark.py          run the classifier over the labeled corpus, print accuracy
│   ├── spike_vision.py       Phase-0 sanity check: PNG → vision model
│   └── corpus/               the labeled trace zips + manifest (source of demo_data)
│
├── Dockerfile                multi-stage: node builds web/ → python-only runtime
├── docker-compose.yml        one service, one command, keys from .env at runtime
├── render.yaml               Render blueprint (the live deploy)
├── requirements.txt          pinned Python deps
├── .env.example              provider-key template
├── APPROACH.md               design writeup  ·  video.md  walkthrough link
```

---

## Run the online webapp

### Option A — just open the live URL

**https://flakylens.onrender.com** (Render free plan; the first request after idle may take
a few seconds to wake the container).

### Option B — one command with Docker

```bash
cp .env.example .env        # then edit .env and set ONE provider key (see below)
docker compose up --build   # builds the image and runs it
# open http://localhost:8000
```

The image is multi-stage: a `node:22-slim` stage builds the React app into `web/dist`, then
a `python:3.14-slim` stage ships a **Python-only** runtime (no Node, npm, or build tools).
Provider keys are injected at runtime from your local `.env` (`env_file` in compose) and are
**never baked into the image**.

### Option C — local dev without Docker (two processes)

```bash
# 1. Backend (FastAPI on :8000) — reads keys from .env via load_dotenv()
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (Vite dev server on :5173) — in a second terminal
cd web && npm install && npm run dev
```

In dev, Vite serves the UI on **:5173** and proxies the API paths (`/diagnose`, `/corpus`,
`/models`, `/benchmark`, `/health`) to FastAPI on **:8000** — same-origin, no CORS. In
production there is no Vite: FastAPI serves the built `web/dist` at `/`, so everything is one
origin on **:8000**. (For a production-like single process locally: `cd web && npm run
build`, then just run uvicorn — it picks up `web/dist` automatically.)

### Trying it out

- **Upload & Diagnose** (left pane) — drop a `trace.zip` and get a diagnosis. **To test
  this, download a failing trace from [`harness/corpus/`](harness/corpus/)** —
  `stale_selector.zip`, `real_bug.zip`, `flaky_timing.zip`, or `network_failure.zip` — and
  upload it. (The `*.baseline.zip` files are *passing* traces; the four named above are the
  injected failures.)
- **Try It on Known Bugs** (right pane) — the same four traces are wired in as a corpus
  browser; it hides each trace's known cause until you diagnose it, then shows the model's
  guess against the truth.
- **Benchmark** — accuracy + confusion matrix from the committed snapshot; it recomputes
  live in-page once you've diagnosed every corpus trace this session.

### Provider keys & the model selector

Any **one** provider key is enough. With no explicit choice, the backend selects the first
provider in this order whose key is set (see `app/llm/factory.py` — the **code is the
source of truth**; `render.yaml` / `.env.example` document a subset):

| Order | Provider      | Env var             | Default model            |
| ----- | ------------- | ------------------- | ------------------------ |
| 1     | Anthropic     | `ANTHROPIC_API_KEY` | Claude Haiku 4.5         |
| 2     | OpenAI        | `OPENAI_API_KEY`    | `gpt-4o`                 |
| 3     | GitHub Models | `GITHUB_TOKEN`      | `openai/gpt-4o-mini`     |
| 4     | OpenRouter    | `OPENROUTER_API_KEY`| `nvidia/nemotron-nano-12b-v2-vl:free` |

Obvious `xxxxx` placeholders from `.env.example` are ignored, so a copied stub never selects
the wrong provider. The header dropdown calls `GET /models`, which does a real one-token ping
per configured provider (cached briefly): working models are selectable, the rest are greyed
out with a reason ("no API key", "key rejected", "model not accessible", "rate limited"…).

---

## API reference

All routes are served by `app/main.py` on port 8000.

| Method & path                  | Purpose                                                                 |
| ------------------------------ | ----------------------------------------------------------------------- |
| `GET /health`                  | Liveness check → `{"status": "ok"}`.                                     |
| `GET /models`                  | Configured providers + live availability → `[{id, label, model, available, reason}]`. |
| `POST /diagnose`               | Diagnose an uploaded `trace.zip` (multipart `file`, optional `model`). **Flat** result: `{category, confidence, reasoning}`. |
| `GET /corpus`                  | List the seeded corpus traces and their known labels.                   |
| `GET /corpus/{name}/diagnose`  | Diagnose one seeded trace (e.g. `real_bug`) alongside its true label. **Nested**: `{name, true_label, diagnosis}`. |
| `GET /benchmark`               | The saved benchmark accuracy + confusion matrix.                        |

```bash
# Diagnose a trace from the command line
curl -F file=@harness/corpus/real_bug.zip http://localhost:8000/diagnose
# → {"category":"real_bug","confidence":0.9,"reasoning":"The test expects 1 element…"}
```

**Bad uploads are rejected at the boundary (HTTP 422), never sent to the model** as a
confident fake diagnosis:
- *Not a trace* — a corrupt/non-zip file, or a zip with no Playwright trace streams.
- *Insufficient evidence* — a real trace archive that yields nothing usable (no error
  context, DOM snapshot, actions, or network entries).

---

## How a diagnosis works

```
trace.zip ──► ingest.py ──► EvidenceBundle ──► [guard] ──► classifier.py ──► DiagnosisResult
              (pure Python)                                 (+ screenshot)     (Pydantic-validated)
```

1. **Ingest** (`app/diagnosis/ingest.py`) — opens the zip with `zipfile` and parses the
   newline-delimited JSON trace streams in **pure Python** (no Node, no `playwright` CLI). It
   distills only the useful signals into an `EvidenceBundle`: the actions, the failure (error
   type, message, failed selector, call log), console messages, network requests, the **DOM
   page snapshot** (the accessibility tree from the trace's `error-context` attachment at the
   moment of failure), and a reference to the failure screenshot.
2. **Evidence guard** (`evidence_sufficiency`) — runs right after extraction. If *all* of
   error-context, DOM snapshot, actions, and network are empty, it refuses to call the model
   and the upload is rejected. Any one present signal is enough (a UI-only test makes no
   network requests, a passing trace has no failure).
3. **Classify** (`app/diagnosis/classifier.py`) — builds a prompt with a disambiguation
   guide, attaches the screenshot (extracted to a temp file, cleaned up after), and asks the
   vision LLM for a single JSON object. It requests JSON mode and falls back to prompt+parse
   if a provider doesn't support it. The result is validated into
   `DiagnosisResult{category, confidence (0–1), reasoning}`.

The whole diagnosis path is provider-agnostic: every model sits behind one `LLMClient`
interface (`app/llm/`), so Anthropic (its own SDK) and the OpenAI-compatible providers
(OpenAI, GitHub Models, OpenRouter) are swappable without touching the diagnosis code.

---

## Run the offline harness

The harness regenerates the labeled corpus and scores the classifier. It needs Node and a
browser; it is **not** part of the deployed app.

```bash
cd harness
npm install
npx playwright install chromium     # one-time: download the browser

# Regenerate the labeled corpus (drives a real browser, then collects + labels traces)
npm run corpus                       # → corpus/*.zip + corpus/manifest.json

# Score the classifier against that corpus (run from the REPO ROOT, needs a provider key)
cd .. && python -m harness.benchmark
# → prints accuracy + a confusion matrix, writes harness/benchmark_results.json
```

**What's being tested:** `harness/sut/` is "Fruit Finder", a tiny static search app — it
fetches eight fruits and filters them client-side as you type. It is explicitly **not** the
product; it's just a stable target to break in known ways. `server.mjs` is a throwaway static
server that Playwright auto-starts on **:5173**.

**How the four failures are injected** (one variable each, so the ground-truth label is
unambiguous):

| Category          | Injection                                                                 |
| ----------------- | ------------------------------------------------------------------------- |
| `stale_selector`  | Test targets the old `#search-box` id; the box is now `#search`.          |
| `network_failure` | Playwright `route` fails `GET /api/fruits.json` with HTTP 503.            |
| `real_bug`        | `?inject=real_bug` inverts the filter, so search returns the *non*-matching fruits. |
| `flaky_timing`    | `?inject=flaky` paints the result ~3s late; the test asserts within 1.5s. |

`spike_vision.py` is a one-off Phase-0 check that a PNG round-trips through the vision model:
`python -m harness.spike_vision <screenshot.png>`.

---

## Tests

```bash
# Backend evidence-guard unit tests (pytest is not a dependency — runs standalone)
python -m app.tests.test_evidence_guard

# Harness Playwright specs (the stale-selector test fails ON PURPOSE, so this exits non-zero)
cd harness && npm test
```

---

## Known limits

Covered in depth in **[APPROACH.md](APPROACH.md)**; the short version:

- **`flaky_timing` vs `real_bug` is the hard boundary.** Both surface as the same symptom —
  an assertion that expected one count and got another — and a single trace records what
  *happened*, not what *would* happen with more time. The committed benchmark snapshot is
  4/4, but the model can flip these two on other runs, which is why the UI frames the
  benchmark as a representative run and always shows confidence + reasoning, not just a label.
- **A malformed-but-valid-looking zip is the other soft spot.** The boundary guard catches
  non-traces and empty evidence, but a zip with a trace-like structure yet corrupt or
  unexpected internals can still slip through and get an over-confident guess.

---

## More

- **[APPROACH.md](APPROACH.md)** — why this problem, key decisions and tradeoffs, what was
  intentionally left out, what breaks first, and what I'd build next.
- **[video.md](video.md)** — the walkthrough link.
