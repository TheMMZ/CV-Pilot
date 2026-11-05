# CV Pilot

The agreed application stack is Python, Streamlit, PostgreSQL, GitHub API, LLM integration, Python PDF generation, and Python Playwright.

- Put business logic and integrations in cvpilot/. The main workspace is streamlit_app.py.
- run.py launches the Python landing server and Streamlit. No Node.js runtime or SQLite fallback.
- PostgreSQL credentials and provider keys belong in the ignored .env file. Never print or commit them.
- The optional scripts/migrate_sqlite.py reads the previous database only to migrate existing user data.
- Keep all CV claims tied to source evidence. Planned projects retain their status. LLM proposals require review.
- Playwright may fill configured forms. Submission requires explicit application approval and a success confirmation; unresolved attempts must not retry automatically.
- Test core logic with pytest, PostgreSQL behavior against a real test database, and Playwright against local fixtures. Do not submit real applications during tests.
- Keep frontend-atlas motion, accessible controls, and reduced-motion fallbacks for the landing page. Read corresponding references before adding effects.
