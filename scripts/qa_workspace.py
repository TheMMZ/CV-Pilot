from pathlib import Path
from playwright.sync_api import sync_playwright
from cvpilot.storage import Store

out = Path('qa');out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    try:
        page = browser.new_page(viewport={'width': 1440, 'height': 1050})
        page.goto('http://127.0.0.1:4317')
        page.get_by_role('link', name='Build my next application').click()
        page.wait_for_url('http://127.0.0.1:8501/**')
        page.get_by_role('heading', name='Your experience. The right opportunity.').wait_for()
        page.get_by_role('button', name='Try a sample', exact=True).click()
        page.get_by_label('Company', exact=True).fill('Migration QA')
        page.get_by_role('button', name='Find my matches', exact=True).click()
        page.get_by_text('Recognized skill coverage', exact=True).wait_for()
        page.screenshot(path=str(out / 'streamlit-desktop.png'), full_page=True)
        with page.expect_download() as download:
            page.get_by_role('button', name='Download PDF preview', exact=True).click()
        download.value.save_as(str(out / 'python-cv-preview.pdf'))
        assert (out / 'python-cv-preview.pdf').read_bytes().startswith(b'%PDF-')
        page.get_by_role('button', name='Save tailored CV', exact=True).click()
        page.get_by_text('CV snapshot saved.', exact=False).wait_for()
        page.get_by_role('link', name='Application tracker', exact=True).click()
        page.get_by_role('heading', name='Your application trail.').wait_for()
        page.get_by_role('button', name='Download tailored CV (PDF)', exact=True).wait_for()
        page.get_by_role('link', name='Connections', exact=True).click()
        page.get_by_role('heading', name='The agreed stack.').wait_for()
        page.get_by_text('PostgreSQL connected', exact=True).wait_for()
        page.get_by_role('link', name='Application studio', exact=True).click()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(out / 'streamlit-mobile.png'), full_page=True)
        assert not page.locator('[data-testid="stException"]').count()
        print('PASS: Python landing -> real Streamlit UI -> matching -> PDF download -> PostgreSQL snapshot -> tracker -> connections -> mobile.')
    finally:
        browser.close()
        with Store().connect() as connection:
            connection.execute("DELETE FROM cv_events WHERE application_id IN (SELECT id FROM cv_applications WHERE payload->'job'->>'company'='Migration QA')")
            connection.execute("DELETE FROM cv_applications WHERE payload->'job'->>'company'='Migration QA'")
