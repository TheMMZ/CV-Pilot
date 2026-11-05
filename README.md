# CV Pilot

A local application workspace that turns a master CV and public GitHub repository evidence into job-specific CV versions.

## Run

Requires Node.js 24+ (uses built-in SQLite).

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:4317 for the landing page, or http://127.0.0.1:4317/app for the workspace. A fresh clone starts with a generic profile. Edit it in Master CV. An optional local `profile.seed.json` can seed a personal profile when the database is first created; it is ignored by Git.

## Working features

- Public GitHub import: repository descriptions, primary languages, README sources, timestamps, and import warnings. Up to 15 recently updated, non-fork, non-archived repositories. No GitHub credentials required. Import refreshes the saved evidence library.
- Job-description matching with a curated skill vocabulary and visible evidence for each match. Planned project tools do not count as demonstrated skills.
- Tailoring preserves experience facts, prioritizes relevant skills and bullets, and suggests relevant repositories. It does not infer proficiency from a README.
- Immutable CV snapshots for each job; later profile edits do not rewrite prior application versions.
- Printable CV preview: Review CV / PDF, then Print / Save as PDF in the browser.
- Application tracker: Draft, Ready, Applied, Interview, Rejected, Offer. Statuses are manual.
- Editable structured master CV, durable local SQLite storage, input validation, local-only binding and origin checks.

## Optional AI agent

The eve agent is a separate, optional capability. The browser studio uses deterministic matching and templates; it does not silently call an LLM.

```powershell
npm run dev         # Terminal 1: local data workspace
npm run agent:dev   # Terminal 2: eve assistant
```

Authenticate using eve's `/login`, or configure `AI_GATEWAY_API_KEY` for Vercel AI Gateway. Then ask the assistant to analyze a job; its typed `analyze_job` tool calls the local workspace. The configured model is the scaffold default. This AI path needs provider credentials and has not been tested with a live paid model.

## Tests

```powershell
npm test
npm run typecheck
npm run test:browser  # Workspace must be running; uses installed Microsoft Edge
```

The browser smoke test creates one clearly labeled sample application and changes its status to Ready. It checks repository rendering using the imported account when present. It never submits an application.

## Architecture

- `src/core.mjs`: skill extraction, evidence matching, fact-preserving tailoring, printable CV rendering.
- `src/server.mjs`: local HTTP API, Zod validation, public GitHub importer, SQLite persistence.
- `public/`: responsive browser workspace (vanilla JS/CSS; no build step).
- `agent/`: eve instructions and typed analysis tool.
- `data/cv-pilot.sqlite`: personal profile, imported repositories, and application snapshots (ignored by Git).
- `profile.seed.json`: local personal seed profile (ignored). `profile.example.json` is a generic template.

## Limits and next work

This is a working first version, not a completed autonomous job applicant. Job descriptions are pasted manually. Matching is keyword-based and does not understand negations, seniority, all skill synonyms, or the difference between mandatory and preferred requirements. Coverage is not an ATS score or a hiring probability.

GitHub imports are public-only and read repository metadata and READMEs, not source code or contributions. A README can describe other people's work; review evidence and authorship before using it. Private-repository OAuth, source-file evidence extraction, automatic refresh, semantic ranking, AI rewriting in the browser, cover letters, and application-form submission remain future work. No jobs are submitted by this version. The tracker can open the original job link for manual application.

This app is for a single local user. Do not expose this server publicly without authentication and deployment hardening. SQLite and the personal seed are unencrypted local files; keep them out of shared repositories. The optional eve agent is a separate provider-connected runtime.

## API

- `GET /api/state`
- `PUT /api/profile`
- `POST /api/github` `{ "username": "TheMMZ" }`
- `POST /api/analyze` `{ "title", "company", "url", "description" }`
- `POST /api/drafts` (same job payload)
- `PATCH /api/applications/:id` `{ "status": "Ready" }`
- `GET /api/applications/:id/resume`

## Design

Uses frontend-atlas (GOATED UI) principles: a focused application workbench, source-linked evidence, restrained CSS feedback, visible keyboard focus, mobile layout, and reduced-motion support. Design tokens and the direction are recorded in `design.json`.

References: [eve](https://eve.dev/docs), [GitHub REST repositories](https://docs.github.com/en/rest/repos/repos), [GitHub README endpoint](https://docs.github.com/en/rest/repos/contents#get-a-repository-readme), [GOATED UI / frontend-atlas](https://github.com/flash-hero/GOATED-UI-SKILL).

## Landing page and motion

The landing page uses native CSS scroll timelines for the hero illustration and sticky walkthrough cards. Static content remains readable without timeline support. A branded loading interstitial and page-entry fades connect the landing page and workspace; workspace tabs use same-document view transitions and URL hash history. Reduced-motion preferences disable scroll motion and minimize page transitions. No animation libraries or remote assets are required.

The landing-to-workspace loading screen checks workspace resources before navigation and supports cancel, retry via a direct link, and reduced motion. This handoff uses the loading screen plus a workspace fade; other workspace tabs retain native view transitions.
