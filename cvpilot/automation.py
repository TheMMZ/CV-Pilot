import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from playwright.sync_api import sync_playwright
from . import DATA_DIR

ALLOWED_FIELDS = {'name', 'email', 'phone', 'github'}

def validate_target(url, allow_local=False):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use a valid HTTP(S) application URL without embedded credentials.')
    host = parsed.hostname.lower()
    try:
        private = not ipaddress.ip_address(host).is_global
    except ValueError:
        private = host in ('localhost', 'localhost.localdomain') or host.endswith(('.local', '.internal'))
    if private and not allow_local:
        raise ValueError('Local/private application URLs are allowed only in the local test fixture.')
    return url

def fill_application(url, profile, pdf_bytes, mapping, submit=False, approved=False,
                     allow_local=False, channel=None, output_dir=None):
    validate_target(url, allow_local)
    if submit and not approved:
        raise ValueError('Review and approve this exact application before submitting.')
    if submit and (not mapping.get('submit_selector') or not mapping.get('confirmation_text')):
        raise ValueError('Submission requires a submit selector and a confirmation message.')
    fields = mapping.get('fields', {})
    if not fields or any(key not in ALLOWED_FIELDS for key in fields):
        raise ValueError('Map form labels to name, email, phone, and/or github.')
    output = Path(output_dir or DATA_DIR / 'automation' / str(uuid4()))
    output.mkdir(parents=True, exist_ok=True)
    pdf_path = output / 'cv.pdf'
    pdf_path.write_bytes(pdf_bytes)
    result = {'state': 'failed', 'clicked': False, 'url': url, 'screenshot': str(output / 'preview.png')}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=channel or os.getenv('PLAYWRIGHT_CHANNEL') or ('msedge' if os.name == 'nt' else None), headless=True)
            try:
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                # Block local network redirects on real external workflows as well as the initial URL.
                def guard(route):
                    target = route.request.url
                    if target.startswith(('http:', 'https:')):
                        try:
                            validate_target(target, allow_local)
                        except ValueError:
                            route.abort()
                            return
                    route.continue_()
                page.route('**/*', guard)
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                for field, label in fields.items():
                    value = profile.get(field, '')
                    if field == 'github' and value:
                        value = 'https://github.com/' + value
                    page.get_by_label(label, exact=True).fill(value, timeout=10000)
                if mapping.get('resume_label'):
                    page.get_by_label(mapping['resume_label'], exact=True).set_input_files(str(pdf_path))
                page.screenshot(path=result['screenshot'], full_page=True)
                result.update(state='prepared', final_url=page.url)
                if submit:
                    confirmation = page.get_by_text(mapping['confirmation_text'], exact=False)
                    if confirmation.is_visible():
                        raise ValueError('The confirmation message is already visible before submission. Use a unique success message.')
                    result['clicked'] = True  # Set before click: a timeout can happen after the request was sent.
                    page.locator(mapping['submit_selector']).click(timeout=15000)
                    confirmation.wait_for(state='visible', timeout=20000)
                    page.screenshot(path=result['screenshot'], full_page=True)
                    result.update(state='submitted', final_url=page.url)
            finally:
                browser.close()
    except Exception as exc:
        result['state'] = 'uncertain' if result['clicked'] else 'failed'
        result['error'] = str(exc)[:1200]
    return result
