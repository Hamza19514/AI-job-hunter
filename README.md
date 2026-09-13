# AI Job Hunter (Saudi Arabia)

A personal Flask app with two Claude-powered agents:

- **Agent 1 (job hunter)** — searches the live web (Google, LinkedIn postings,
  job boards, official employer/government career portals) for currently
  open Saudi Arabia roles, verifies each against an official source, scores
  fit 0-100, and returns only jobs it recommends `APPLY` or
  `APPLY_IMMEDIATELY` — capped at **5 per day**, and never after **4:00 PM
  Asia/Riyadh time**.
- **Agent 2 (applicator)** — automatically takes each job Agent 1 finds and
  generates a tailored resume PDF, a tailored cover letter PDF, and a
  realistic fit-percentage analysis, grounded strictly in the fixed facts in
  `app/resume_data.py` (never invents employers, dates, titles, or metrics).

The dashboard (`/`) shows today's recommended jobs with fit score, the
generated resume/cover-letter PDFs, and the official apply link — fully
automated, no manual review step needed to trigger Agent 2.

## How the pipeline runs

A background scheduler (APScheduler) checks periodically
(`SEARCH_INTERVAL_MINUTES`, default hourly) whether it's still eligible to
search: fewer than `DAILY_JOB_CAP` (default 5) APPLY jobs found today, and
before `SEARCH_CUTOFF_HOUR_LOCAL` (default 16:00) in `APP_TIMEZONE` (default
`Asia/Riyadh`). If eligible, it runs Agent 1, then Agent 2 + PDF generation
for each new job, and stores everything in the database. The dashboard's
"Run search now" button uses the exact same eligibility check, so it's
disabled once the cap or cutoff is hit.

Because this needs an always-on background process, it is **not** suited to
purely serverless hosts (e.g. Vercel). Use an always-on host such as
Render, Railway, or PythonAnywhere.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env and add your ANTHROPIC_API_KEY
python run.py
```

Visit http://localhost:5000

To test without the background scheduler / without hitting the API:
```bash
DISABLE_SCHEDULER=1 python run.py
```

## Getting an Anthropic API key

1. Sign up / log in at https://console.anthropic.com
2. Settings → API Keys → Create Key
3. Settings → Billing → add credit (separate from any claude.ai Pro plan —
   API usage is billed independently, pay-as-you-go)
4. Put the key in `.env` as `ANTHROPIC_API_KEY` (never commit this file)

## Configuration

All tunables live in `config.py` / environment variables — see
`.env.example` for the full list (daily cap, cutoff hour, timezone, models,
search interval).

## Deploying (Render example)

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render, pointing at the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn run:app`
5. Add environment variables from `.env.example` (at least
   `ANTHROPIC_API_KEY` and `SECRET_KEY`) in Render's dashboard.
6. Add a persistent disk mounted at `instance/` so the SQLite DB and
   generated PDFs survive deploys/restarts.

`gunicorn` isn't in `requirements.txt` yet — add it (`pip install gunicorn`
and append to `requirements.txt`) before deploying with the start command
above.

## Project layout

```
app/
  agents/
    job_hunter.py     # Agent 1 — web search + verification + fit scoring
    applicator.py      # Agent 2 — resume/cover-letter tailoring
    anthropic_client.py
  pdf/
    templates/         # HTML/CSS resume + cover letter templates
    render.py           # WeasyPrint HTML -> PDF
  templates/            # dashboard UI (Jinja)
  static/css/
  models.py             # Job, SearchRun (SQLAlchemy)
  scheduler.py           # daily cap + cutoff orchestration
  routes.py
  resume_data.py         # fixed master resume facts (source of truth)
config.py
run.py
```

## Known limitations (MVP)

- Resume PDFs aim for a balanced two pages using the same layout/spacing as
  the reference resume, but exact balance can vary slightly with longer
  tailored content — spot-check PDFs for very verbose job descriptions.
- Agent 2's fabrication guardrails validate that skills/projects/experience
  bullets keep the same items and protected numbers (e.g. `$3M`, `200+`,
  `40%`) as the master resume; it does not do full semantic fact-checking
  beyond that.
- Single-user, no authentication — do not deploy this publicly without
  adding one.
