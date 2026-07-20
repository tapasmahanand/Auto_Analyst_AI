# AutoAnalyst AI

An AI-powered data analysis platform: upload a dataset, ask a question in plain
English, and get an AI-generated analysis plan, automatically written & executed
Python analysis, charts, grounded insights, and a downloadable report.

## How it works

```
Upload (CSV/Excel/JSON/TXT/PDF)
   └─► Dataset inspection (rows, columns, dtypes, missing values, duplicates,
       numeric/categorical/date columns, basic statistics)
        └─► AI planner (OpenAI) — step-by-step analysis plan
             └─► Per step: AI writes Python → sandboxed execution → on error,
                 AI fixes the code (up to MAX_CODE_RETRIES attempts)
                  └─► AI reviewer checks results against your question
                       └─► AI insights grounded in the computed numbers
                            └─► Report: Markdown + HTML (+ PDF when available)
```

- **Backend** — FastAPI · SQLAlchemy/SQLite · Pandas · NumPy · Matplotlib · Jinja2
- **Frontend** — Next.js (App Router) · TypeScript · Tailwind CSS
- **AI** — OpenAI API (key stays on the backend only)

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

### 3. Try it

Upload `sample_data/sales_data.csv` and ask something like:

> Which region drives revenue, and how did sales trend over the first half of 2025?

## Optional: PDF reports

Markdown and HTML reports always work. True PDF export uses WeasyPrint, which
needs system libraries:

```bash
# macOS
brew install pango
# Debian/Ubuntu
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
```

If these are missing the app still runs; the PDF download simply reports that
it is unavailable.

## Configuration

All settings live in `backend/.env` (see `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Backend-only OpenAI key |
| `OPENAI_MODEL` | `gpt-4o` | Model for planning/codegen/review/insights |
| `MAX_UPLOAD_MB` | `50` | Upload size limit |
| `EXEC_TIMEOUT_SECONDS` | `60` | Wall-clock limit per generated script |
| `EXEC_MEMORY_MB` | `2048` | Memory cap per generated script |
| `MAX_CODE_RETRIES` | `3` | AI fix attempts for failing code |
| `MAX_PLAN_STEPS` | `6` | Max steps in an analysis plan |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |

## Deployment

This is **two apps**: a Next.js frontend and a FastAPI (Python) backend. Static
hosts like Netlify and Firebase Hosting can only serve the frontend — the
backend needs a real Python server (persistent process, disk storage, subprocess
sandboxing, SSE streaming). Deploying only the repo to Netlify/Firebase produces
a site that loads but cannot reach its API.

The supported setup: **frontend on Netlify** (config in `netlify.toml`),
**backend on Render** (config in `render.yaml`). Deploy in this order:

### 1. Backend → Render

1. Render dashboard → **New → Blueprint** → select this repo. Render reads
   `render.yaml` and creates the `autoanalyst-backend` web service.
2. Set `OPENAI_API_KEY` when prompted (it is never committed).
3. After the deploy, note the service URL, e.g. `https://autoanalyst-backend.onrender.com`,
   and check `https://<name>.onrender.com/api/health` returns `{"status": "ok", ...}`
   with `openai_configured: true`.

### 2. Frontend → Netlify

1. Netlify → **Add new site → Import an existing project** → select this repo.
   `netlify.toml` supplies the base directory (`frontend`), build command, and
   Next.js runtime — no manual build settings needed.
2. **Before deploying**, add the environment variable
   `NEXT_PUBLIC_API_BASE = https://<name>.onrender.com` (no trailing slash) under
   *Site configuration → Environment variables*. This value is **baked into the
   JavaScript bundle at build time** — if you add or change it later, you must
   redeploy with **"Clear cache and deploy site"**.

### 3. Close the loop (CORS)

On the Render service, set `CORS_ORIGINS` to your Netlify URL, e.g.
`CORS_ORIGINS=https://your-site.netlify.app` (comma-separate to allow several
origins). Render redeploys automatically.

### Why a plain deploy is broken

- `frontend/lib/api.ts` falls back to `http://localhost:8000` when
  `NEXT_PUBLIC_API_BASE` is unset at **build time** — the deployed site then
  tries to call an API on each visitor's own machine, so every request fails.
- Even with the right API base, the backend's `CORS_ORIGINS` default only allows
  `http://localhost:3000`, so the browser blocks responses from any deployed
  frontend origin.

### Free-tier caveats (Render)

- **No persistent disk**: uploads, run history, reports, and the SQLite DB are
  wiped on every deploy/restart. Upgrade to the Starter plan and uncomment the
  `disk:` block in `render.yaml` (setting `STORAGE_DIR=/var/data/storage`) for
  durable storage.
- **Cold starts**: the service spins down after ~15 min idle; the first request
  after that takes ~50 s.
- **512 MB RAM**: `render.yaml` lowers `EXEC_MEMORY_MB` to 380 so executed
  analysis scripts can't OOM the container.
- **No PDF export**: WeasyPrint's system libraries (pango) can't be installed on
  Render's native Python runtime; reports fall back to Markdown/HTML. If you
  need PDFs, deploy with `backend/Dockerfile` instead (see its header comment).

## Security model

AI-generated code is treated as untrusted:

1. **Static AST gate** — allowlisted imports only (pandas, numpy, matplotlib,
   scipy, …); `os`, `subprocess`, `open`, `eval`, `exec`, `getattr`, dunder
   attribute access, and file/network modules are rejected before execution.
2. **Process isolation** — scripts run in a separate `python -I` subprocess with
   a stripped environment (no API keys) inside a per-run scratch directory that
   contains only a *copy* of the dataset.
3. **Resource limits** — CPU time, memory, and output file size caps plus a
   wall-clock timeout; failed runs are fed back to the AI for correction with a
   bounded retry count.

Uploads are validated by type and size and stored under randomized names in
`storage/` (gitignored), alongside generated code, charts, reports, and the
SQLite session history.

## Tests

```bash
cd backend
./.venv/bin/python -m pytest tests/ -q
```

Covers dataset inspection for all five file types, sandbox policy enforcement
(blocked imports, runtime errors, timeouts), and the full upload → analyze →
report flow with a mocked LLM.

## Project layout

```
backend/app/
  routers/       # /api/datasets, /api/analyses (+SSE events), /api/.../report
  services/
    inspection.py  # deterministic dataset profiling
    executor.py    # sandboxed execution of AI code
    pipeline.py    # plan → code → execute → review → insights → report
    report.py      # Jinja2 → Markdown/HTML, WeasyPrint → PDF
    llm.py         # OpenAI wrapper
  prompts/       # agent prompt templates
  templates/     # report templates
backend/tests/
frontend/        # Next.js app
sample_data/     # sample dataset for testing
storage/         # runtime data (gitignored)
```
