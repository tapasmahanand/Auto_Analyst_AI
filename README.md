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

## Example analysis output

A real run of the app against a 500-row × 28-column sales/customer dataset,
for the prompt *"Summarize the dataset and highlight data quality issues."*
This is the actual generated report, reproduced in full below.

### Executive summary

The dataset comprises 500 rows and 28 columns, providing a detailed view of
sales transactions. It is complete with no missing or duplicate values,
indicating high data integrity. However, there are data quality concerns,
including unexpected values in the `Gender` column and outliers in several
numeric columns, which may affect the reliability of the analysis.

### Dataset overview

| Field | Value |
|---|---|
| File | `sales_customer_dataset.csv` (CSV) |
| Rows × Columns | 500 × 28 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Numeric columns | `Customer_Age`, `Quantity`, `Unit_Price`, `Discount_Percent`, `Gross_Sales`, `Discount_Amount`, `Net_Sales`, `Cost`, `Profit`, `Profit_Margin_Percent`, `Customer_Satisfaction`, `Returned` |
| Categorical columns | `Order_ID`, `Customer_ID`, `Customer_Name`, `Gender`, `City`, `State`, `Region`, `Customer_Segment`, `Sales_Channel`, `Product_Category`, `Product_Subcategory`, `Payment_Method`, `Salesperson`, `Loyalty_Member` |
| Date columns | `Order_Date`, `Ship_Date` |

### AI-generated analysis plan

All 6 steps completed:

1. **Provide an overview of the dataset's structure and basic statistics** — `df.head()` and `df.describe()` for basic statistics on numeric columns.
2. **Identify potential data quality issues related to missing values** — `df.isnull().sum()`, confirming no missing values.
3. **Detect any duplicate rows in the dataset** — `df.duplicated().sum()`, confirming no duplicate rows.
4. **Identify any unusual or unexpected values in categorical columns** — `value_counts()` on categorical columns such as `Gender`, surfacing an unexpected `Other` category.
5. **Identify outliers in numeric columns** — box plots for `Unit_Price`, `Gross_Sales`, and `Profit` via matplotlib.
6. **Summarize data quality issues found** — compiled the findings and recommendations below.

### Key findings

- The dataset is complete with no missing values across all columns. *(Total missing values: 0)*
- There are no duplicate rows in the dataset. *(Duplicate rows count: 0)*
- Unexpected value `Other` found in the `Gender` column. *(Gender unique values: 3, top: `Other`, freq: 174)*
- Outliers detected in numeric columns such as `Gross_Sales`, `Discount_Amount`, and `Profit`. *(Gross_Sales max: 35678.1, Discount_Amount max: 6936.52, Profit max: 12968.3)*

### Charts

**Data quality**

![Missing values by column](examples/charts/step2_missing_values.png)

**Categorical column distributions**

![City value counts](examples/charts/step4_City_value_counts.png)
![Customer ID value counts](examples/charts/step4_Customer_ID_value_counts.png)
![Customer Name value counts](examples/charts/step4_Customer_Name_value_counts.png)
![Customer Segment value counts](examples/charts/step4_Customer_Segment_value_counts.png)
![Gender value counts](examples/charts/step4_Gender_value_counts.png)
![Loyalty Member value counts](examples/charts/step4_Loyalty_Member_value_counts.png)
![Order ID value counts](examples/charts/step4_Order_ID_value_counts.png)
![Payment Method value counts](examples/charts/step4_Payment_Method_value_counts.png)
![Product Category value counts](examples/charts/step4_Product_Category_value_counts.png)
![Product Subcategory value counts](examples/charts/step4_Product_Subcategory_value_counts.png)
![Region value counts](examples/charts/step4_Region_value_counts.png)
![Sales Channel value counts](examples/charts/step4_Sales_Channel_value_counts.png)
![Salesperson value counts](examples/charts/step4_Salesperson_value_counts.png)
![State value counts](examples/charts/step4_State_value_counts.png)

**Outlier detection**

![Gross Sales boxplot](examples/charts/step5_Gross_Sales_boxplot.png)
![Profit boxplot](examples/charts/step5_Profit_boxplot.png)
![Unit Price boxplot](examples/charts/step5_Unit_Price_boxplot.png)
![Unit price outliers](examples/charts/step6_unit_price_outliers.png)

### Recommendations

- Investigate and address the unexpected `Other` value in the `Gender` column to ensure data accuracy.
- Review and potentially adjust outliers in numeric columns to prevent skewed analysis results.

### Limitations

- The dataset includes future dates (2025), which may not align with current data trends.
- Presence of outliers in several numeric columns could skew analysis results if not addressed.

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
examples/        # example generated report(s)
storage/         # runtime data (gitignored)
```
