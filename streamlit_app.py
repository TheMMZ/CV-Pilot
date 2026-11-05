import copy
import hashlib
import json
import os
from pathlib import Path
import streamlit as st
from pydantic import ValidationError
from cvpilot import ROOT
from cvpilot.models import Job, Profile
from cvpilot.storage import Store, STATUSES
from cvpilot.github import import_repositories
from cvpilot.matching import analyze, tailor
from cvpilot.llm import llm_configured, propose, accept_proposal
from cvpilot.documents import resume_pdf
from cvpilot.browser_jobs import run_browser_job

st.set_page_config(page_title='CV Pilot | Application workspace', page_icon='↗', layout='wide')
st.html('''<style>
[data-testid="stSidebar"]{background:#182a42;color:#fff}
[data-testid="stSidebar"] a,[data-testid="stSidebar"] p,[data-testid="stSidebar"] span{color:#d2e0f4}
.block-container{max-width:1300px;padding-top:2.7rem}
h1{letter-spacing:-1.5px}h2{letter-spacing:-.7px}
[data-testid="stVerticalBlockBorderWrapper"]{background:white;border-radius:12px}
div[data-testid="stMetric"]{background:#edf3fd;padding:17px;border-radius:8px}
@keyframes panel-enter{from{opacity:.5;translate:0 5px}}
@media(prefers-reduced-motion:no-preference){[data-testid="stMainBlockContainer"]{animation:panel-enter 180ms ease-out}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>''')

@st.cache_resource
def database():
    store = Store()
    store.initialize()
    return store

try:
    store = database()
except Exception:
    st.title('Connect PostgreSQL')
    st.error('PostgreSQL is not available. Configure DATABASE_URL in .env and start the database with docker compose up -d postgres.')
    st.stop()

def repositories():
    return store.get('github', {}).get('repositories', [])

def introduction(eyebrow, title, subtitle):
    st.caption(eyebrow.upper())
    st.title(title)
    st.write(subtitle)

def review_profile(profile):
    st.subheader(profile['name'])
    st.caption(profile['headline'])
    st.write(profile['summary'])
    st.markdown('**Skills:** ' + ', '.join(profile['skills']))
    for exp in profile['experience']:
        st.markdown('**' + exp['title'] + ' — ' + exp['organization'] + '**')
        st.caption(exp['dates'])
        for bullet in exp.get('bullets', []):
            st.write('• ' + bullet)
    for project in profile['projects']:
        st.markdown('**' + project['name'] + '** · ' + project['status'])
        st.write(project['description'])

def studio():
    introduction('Application studio', 'Your experience. The right opportunity.', 'Match a job to your evidence, tailor your CV, and prepare a reviewed application.')
    left, right = st.columns([1.08, 1], gap='large')
    with left, st.container(border=True):
        st.subheader('The opportunity')
        sample = st.button('Try a sample')
        if sample:
            st.session_state.update(job_title='Data Engineering Intern', job_company='Sample company', job_url='',
                job_description='Build data pipelines using Python, SQL, PostgreSQL and Docker. Git and REST APIs are required. Snowflake and Airflow are desirable for this final-year data engineering internship.')
        with st.form('job'):
            title = st.text_input('Job title', key='job_title')
            company = st.text_input('Company', key='job_company')
            url = st.text_input('Application URL', key='job_url')
            description = st.text_area('Job description', height=220, key='job_description')
            matched = st.form_submit_button('Find my matches', type='primary', use_container_width=True)
        if matched:
            try:
                job = Job(title=title, company=company, url=url, description=description).model_dump()
                profile = store.get('profile')
                st.session_state.draft = tailor(profile, repositories(), job)
                st.session_state.pop('llm_proposal', None)
            except ValidationError as exc:
                st.error('; '.join(str(e['loc'][0]) + ': ' + e['msg'] for e in exc.errors()))
    draft = st.session_state.get('draft')
    with right, st.container(border=True):
        st.subheader('Your evidence')
        if not draft:
            st.info('Paste a job description to compare it with your master CV and GitHub repositories.')
            st.caption(f'{len(repositories())} imported repositories · PostgreSQL connected')
        else:
            analysis = draft['analysis']
            st.metric('Recognized skill coverage', f'{analysis["score"]}%' if analysis['score'] is not None else 'Unknown',
                      help=analysis['method'])
            for match in analysis['matched']:
                with st.expander('✓ ' + match['skill']):
                    for evidence in match['evidence']:
                        st.markdown('**' + evidence['source'] + '**')
                        st.write(evidence['note'])
                        if evidence.get('url'):
                            st.link_button('View repository', evidence['url'])
            st.markdown('**Requirements without evidence**')
            st.write(', '.join(analysis['missing']) or 'No gaps among the recognized skills.')
            st.caption(analysis['method'])
            if st.button('Save tailored CV', type='primary', use_container_width=True):
                application_id = store.create_application(draft)
                st.session_state.selected_application = application_id
                st.success('CV snapshot saved. Open Application tracker to download the PDF and prepare the application.')
            st.download_button('Download PDF preview', resume_pdf(draft), 'cv-preview.pdf', 'application/pdf', use_container_width=True)
    if not draft:
        return
    st.divider()
    st.subheader('LLM tailoring')
    st.write('Generate revised wording and a cover letter with references to your saved facts. Review the proposal before saving it.')
    if not llm_configured():
        st.info('Choose an OpenAI-compatible provider in .env: LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL. Local Ollama endpoints are supported. Matching and PDF generation work without an LLM.')
    if st.button('Generate AI proposal', disabled=not llm_configured()):
        try:
            with st.spinner('Tailoring wording against your source facts…'):
                st.session_state.llm_proposal = propose(store.get('profile'), repositories(), draft['job'])
        except Exception as exc:
            st.error('Could not generate an accepted proposal. ' + (str(exc) if isinstance(exc, (ValueError, RuntimeError)) else 'Check your provider settings and model access.'))
    generated = st.session_state.get('llm_proposal')
    if generated:
        proposal = generated['proposal']
        st.write(proposal['rationale'])
        st.markdown('**Suggested profile**')
        st.write(proposal['summary']['text'])
        for rewrite in proposal['rewrites']:
            with st.expander('Review revised experience bullet'):
                st.caption('Original source')
                st.write(generated['sources'][rewrite['source_id']]['text'])
                st.caption('Suggested wording')
                st.write(rewrite['text'])
        with st.expander('Cover letter and source references'):
            st.write(proposal['cover_letter']['text'])
            for source_id in set(proposal['cover_letter']['source_ids'] + proposal['summary']['source_ids']):
                st.caption(source_id)
                st.write(generated['sources'][source_id]['text'])
        reviewed = st.checkbox('I reviewed the AI wording and verified that every claim reflects my actual experience.')
        if st.button('Save reviewed AI version', disabled=not reviewed, type='primary'):
            try:
                result = accept_proposal(draft, generated)
                application_id = store.create_application(result)
                st.session_state.selected_application = application_id
                st.success('Reviewed AI version and cover letter saved in the application tracker.')
            except ValueError as exc:
                st.error(str(exc))

def evidence():
    introduction('GitHub evidence', 'The work behind the words.', 'Import repository descriptions, primary languages, and README evidence from your GitHub account.')
    with st.form('github-import'):
        username = st.text_input('GitHub username', value=store.get('profile')['github'])
        importing = st.form_submit_button('Import repositories', type='primary')
    st.caption('Public repositories require no credentials. To include private repositories you own, configure a read-only GITHUB_TOKEN in .env.')
    if importing:
        try:
            with st.spinner('Reading GitHub repository evidence…'):
                imported = import_repositories(username.strip())
                store.put('github', imported)
            st.success(f'Imported {len(imported["repositories"])} repositories for {imported["username"]}.')
        except Exception as exc:
            st.error(str(exc) if isinstance(exc, (RuntimeError, ValueError)) else 'GitHub could not be reached. Try again.')
    imported = store.get('github', {})
    for warning in imported.get('warnings', []):
        st.warning(warning)
    cols = st.columns(2)
    for i, repo in enumerate(imported.get('repositories', [])):
        with cols[i % 2], st.container(border=True):
            st.subheader(repo['name'])
            st.write(repo.get('description', ''))
            st.caption(' · '.join(repo['languages']) + ' · ' + ('Private' if repo.get('private') else 'Public'))
            st.link_button('Open repository', repo['url'])
            with st.expander('Read source evidence'):
                st.text(repo.get('readme') or 'No README available.')

def tracker():
    introduction('Application tracker', 'Your application trail.', 'Download a real PDF, review each version, and prepare a configured application form.')
    applications = store.applications()
    if not applications:
        st.info('Save a tailored CV in Application studio to create your first application.')
        return
    ids = [a['id'] for a in applications]
    selected = st.session_state.get('selected_application')
    application_id = st.selectbox('Saved application', ids, index=ids.index(selected) if selected in ids else 0,
                                  format_func=lambda value: next(a['job']['title'] + ' — ' + a['job']['company'] + ' · ' + a['created'][:10] for a in applications if a['id'] == value))
    application = store.application(application_id)
    st.session_state.selected_application = application_id
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(application['job']['title'] + ' — ' + application['job']['company'])
        st.caption('Saved ' + application['created'][:10] + ' · PostgreSQL snapshot')
    with col2:
        with st.form('status-' + application_id):
            status = st.selectbox('Application status', STATUSES, index=STATUSES.index(application['status']))
            if st.form_submit_button('Update status'):
                store.set_status(application_id, status)
                st.success('Status updated.')
    pdf = resume_pdf(application)
    st.download_button('Download tailored CV (PDF)', pdf, 'CV-' + application_id[:8] + '.pdf', 'application/pdf', type='primary')
    if application.get('cover_letter'):
        st.download_button('Download cover letter', application['cover_letter'], 'cover-letter.txt', 'text/plain')
    with st.expander('Review saved CV', expanded=False):
        review_profile(application['profile'])
    st.divider()
    st.subheader('Prepare application with Playwright')
    st.write('Map the form’s exact field labels, prepare a preview, then approve submission. Login, CAPTCHA, custom widgets, and unsupported forms may require manual completion.')
    target_url = application['job'].get('url', '')
    st.write('**Destination:** ' + (target_url or 'No application URL was saved. Create a new version with the application URL.'))
    mapping_text = st.text_area('Form mapping (JSON)', json.dumps({'fields': {'name': 'Full name', 'email': 'Email'},
        'resume_label': 'Resume', 'submit_selector': 'button[type="submit"]', 'confirmation_text': 'Thank you for applying'}, indent=2), height=210, key='mapping-' + application_id)
    try:
        mapping = json.loads(mapping_text)
    except ValueError:
        st.warning('Enter valid JSON for the form mapping.')
        return
    prepared_key = 'prepared-' + application_id
    fingerprint = json.dumps(mapping, sort_keys=True) + target_url
    if st.button('Prepare form preview', disabled=not target_url):
        with st.spinner('Filling the application form without submitting…'):
            result = run_browser_job(target_url, application['profile'], pdf, mapping)
        store.record_automation(application_id, result)
        st.session_state[prepared_key] = {'fingerprint': fingerprint, 'result': result}
    prepared = st.session_state.get(prepared_key)
    if prepared and prepared['fingerprint'] == fingerprint:
        result = prepared['result']
        if result['state'] == 'prepared':
            st.success('Form prepared. Review the screenshot and the downloaded CV before submitting.')
            if result.get('screenshot') and Path(result['screenshot']).exists():
                st.image(result['screenshot'])
        elif result.get('error'):
            st.error(result['error'])
    ready = bool(prepared and prepared['fingerprint'] == fingerprint and prepared['result']['state'] == 'prepared')
    approved = st.checkbox('I reviewed this CV, the filled form, and the destination. Submit this exact application.', key='approve-' + application_id + hashlib.sha256(fingerprint.encode()).hexdigest()[:12])
    if st.button('Submit approved application', disabled=not (ready and approved and application['submit_state'] == 'idle'), type='primary'):
        try:
            store.claim_submission(application_id)
            with st.spinner('Submitting the approved application and checking its confirmation…'):
                result = run_browser_job(target_url, application['profile'], pdf, mapping, submit=True, approved=True)
            store.record_automation(application_id, result, submitting=True)
            if result['state'] == 'submitted':
                st.success('Submission confirmed. Application marked Applied.')
            else:
                st.warning(result.get('error', 'Submission could not be confirmed. Review the site before retrying.'))
        except ValueError as exc:
            st.error(str(exc))
    with st.expander('Application activity'):
        for event in store.events(application_id):
            st.write(event['created'].isoformat() + ' · ' + event['event'])
            if event['details'].get('error'):
                st.caption(event['details']['error'])

def profile_page():
    introduction('Master CV', 'Your source of truth.', 'Keep your experience and project status accurate. Saved applications keep their own snapshots.')
    profile = store.get('profile')
    updated = st.text_area('Profile JSON', json.dumps(profile, indent=2, ensure_ascii=False), height=550)
    if st.button('Save master CV', type='primary'):
        try:
            profile = Profile.model_validate_json(updated).model_dump()
            store.put('profile', profile)
            st.session_state.pop('draft', None)
            st.session_state.pop('llm_proposal', None)
            st.success('Master CV saved in PostgreSQL.')
        except ValidationError as exc:
            st.error('Profile validation failed. Check required fields and project statuses.')
        except ValueError:
            st.error('Invalid JSON.')
    with st.expander('Current profile preview'):
        review_profile(profile)

def settings():
    introduction('Connections', 'The agreed stack.', 'Python · Streamlit · PostgreSQL · GitHub API · LLM · ReportLab PDF · Playwright')
    st.success('PostgreSQL connected')
    st.info('LLM configured' if llm_configured() else 'LLM needs LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env.')
    st.write('Model:', os.getenv('LLM_MODEL') or 'Not configured')
    st.write('GitHub:', 'Read-only token configured' if os.getenv('GITHUB_TOKEN') else 'Public repository access')
    st.write('Playwright browser:', os.getenv('PLAYWRIGHT_CHANNEL', 'msedge'))
    st.caption('Provider credentials stay in the local environment and are not displayed here.')

pages = [st.Page(studio, title='Application studio', icon=':material/work:', default=True),
         st.Page(evidence, title='GitHub evidence', icon=':material/code:'),
         st.Page(tracker, title='Application tracker', icon=':material/view_kanban:'),
         st.Page(profile_page, title='Master CV', icon=':material/person:'),
         st.Page(settings, title='Connections', icon=':material/settings:')]
nav = st.navigation(pages)
with st.sidebar:
    st.markdown('### ↗ CV Pilot')
    st.caption('Python + PostgreSQL workspace')
    st.write(store.get('profile')['name'])
    st.markdown('[← Landing page](http://127.0.0.1:' + os.getenv('LANDING_PORT', '4317') + ')')
nav.run()
