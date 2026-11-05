# CV Pilot

A GitHub-aware CV and job application assistant built with the agreed stack:

| Component | Technology |
| --- | --- |
| Application and business logic | Python |
| Main workspace | Streamlit |
| Profiles, GitHub evidence, CV versions, tracking and activity | PostgreSQL / JSONB with psycopg |
| Repository ingestion | GitHub REST API via httpx |
| CV wording and cover letters | OpenAI-compatible LLM API via the Python SDK |
| Downloadable CV documents | ReportLab PDF generation |
| Application-form preparation and approved submission | Python Playwright |

The animated landing page is served by a small Python FastAPI server. Its HTML/CSS/JavaScript handles presentation only. There is no Node.js, eve, or SQLite application runtime.

## Start on Windows

Requires Python 3.12+, Docker Desktop, and Microsoft Edge.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts/setup_env.py
docker compose up -d --wait postgres
.venv\Scripts\python.exe run.py
```

Or run `Start-CVPilot.ps1`, which performs initial setup, starts PostgreSQL, imports any previous local data, and launches the app.

- Landing page: http://127.0.0.1:4317
- Streamlit workspace: http://127.0.0.1:8501

A fresh database uses `profile.example.json`. An ignored local `profile.seed.json` can supply a personal starting profile. Edit your profile in **Master CV**.

The launcher starts both Python services and stops them on Ctrl+C. PostgreSQL remains in its Docker volume. `docker compose stop` stops the database without deleting its data. Do not run `docker compose down -v` unless you intend to delete the database volume.

On Linux/macOS, use `.venv/bin/python` and run `python -m playwright install --with-deps chromium`. Leave `PLAYWRIGHT_CHANNEL` unset to use that installed Chromium browser.

## Configure LLM tailoring

The integration is implemented in `cvpilot/llm.py` and exposed in **Application studio**. Set these values in the ignored `.env` file:

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-provider-key
LLM_MODEL=a-model-you-can-access
```

Choose a model supporting Chat Completions and JSON mode. For a locally installed OpenAI-compatible model, set its local base URL and model name; for Ollama the base URL is typically `http://127.0.0.1:11434/v1` and the SDK can use a placeholder API key such as `ollama`.

The app sends the job description and selected source facts to the configured model. Credentials are read from the environment, never from GitHub or Codex sessions. No provider credential is bundled. Matching, PDF export, and tracking work before provider configuration; the AI action clearly remains disabled until configured.

The model returns a summary, revised experience bullets, a cover letter, and source references. Pydantic validates the response, and the app rejects unknown sources, unsupported recognized skills, and new numerical claims. These checks do not prove semantic faithfulness: review the proposed text and source references, then explicitly accept it to save an AI-tailored version. Employment identities, roles, dates, and project statuses are preserved.

## GitHub evidence

Enter your GitHub username in **GitHub evidence**. Public imports require no token. Imports read up to 15 recent owned repositories, excluding forks and archived projects, and collect descriptions, primary languages, and READMEs.

For private repositories you own, set `GITHUB_TOKEN` in `.env` with read-only metadata and contents permissions. The token must belong to the entered account. The importer filters results to that account and never stores the token in PostgreSQL. GitHub rate limits and token permissions still apply. Repository text is evidence for review, not proof of authorship or proficiency.

## Application workflow

1. Maintain your master profile and import GitHub evidence.
2. Paste a job title, company, full description, and application URL.
3. Review skill matches and missing requirements; generate an optional LLM proposal.
4. Save a separate CV snapshot for the job. Download the actual PDF, plus a cover letter when generated.
5. In **Application tracker**, configure the form's exact labels, file input label, submit selector, and unique confirmation message.
6. Prepare a Playwright preview. This fills the target form and uploads the selected CV but does not click Submit.
7. Review the preview and CV, then explicitly approve that exact destination and mapping. The submission action clicks Submit and marks the application Applied only when the configured success message becomes visible.

Example form mapping:

```json
{
  "fields": {"name": "Full name", "email": "Email"},
  "resume_label": "Resume",
  "submit_selector": "button[type=submit]",
  "confirmation_text": "Thank you for applying"
}
```

Label mappings support name, email, phone, and GitHub profile. The current adapter targets standard labeled HTML controls; authentication, CAPTCHA, custom upload widgets, iframes, and site-specific questions may need manual completion or a dedicated adapter. There is no claim of universal job-board support.

Submission attempts are recorded. A confirmed submission cannot be replayed; an ambiguous outcome is locked rather than retried automatically. Status updates are also available manually. No real employer application is sent during tests.

## Storage and migration

PostgreSQL is the only application database. Profiles, repository evidence, saved CV versions, and application events use JSONB and transactional writes. Saved versions remain independent of later profile edits.

To migrate the previous local version:

```powershell
.venv\Scripts\python.exe scripts/migrate_sqlite.py
```

This script reads `data/cv-pilot.sqlite` once, copies its saved profile, GitHub evidence, and applications into PostgreSQL, and records a migration marker. The original file is preserved. SQLite is used only inside this one-time migration utility, never by the running app.

`.env`, `profile.seed.json`, `data/`, `.venv/`, and `qa/` are ignored by Git. PostgreSQL files live in the Docker volume. Browser previews and generated local files live under `data/automation/`.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m scripts.qa_workspace
```

The 13 tests cover skill matching, source preservation, real PDF extraction, GitHub HTTP contracts, the LLM SDK request/response contract, invalid LLM claims, real PostgreSQL snapshots/submission guards, and Playwright form filling plus approved submission against a local fixture.

PostgreSQL tests create an isolated temporary schema when `DATABASE_URL` is configured; otherwise that integration test is explicitly skipped. The browser smoke check requires the app running and creates/removes a clearly labeled QA application. A live paid LLM provider is not required for tests and has not been exercised without a configured key/model.

## Source map

- `streamlit_app.py`: Streamlit application studio, evidence library, tracker, profile editor, and connections.
- `cvpilot/matching.py`: skill extraction, source catalog, matching, fact-preserving prioritization.
- `cvpilot/github.py`: public/private owned-repository import.
- `cvpilot/llm.py`: API-backed proposals, validation, and reviewed acceptance.
- `cvpilot/documents.py`: real PDF document generation.
- `cvpilot/storage.py`: PostgreSQL persistence and submission guards.
- `cvpilot/automation.py`: Python Playwright form adapter.
- `cvpilot/browser_jobs.py`: separate browser worker to support Streamlit on Windows.
- `cvpilot/web.py`: Python landing server and workspace redirect.
- `public/landing.*`: frontend-atlas landing page and loading interstitial.

The app is designed for a single local user. Public multi-user hosting requires authentication, per-user data isolation, managed credentials, and deployment configuration.
