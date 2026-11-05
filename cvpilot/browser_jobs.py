import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from . import DATA_DIR, ROOT

def run_browser_job(url, profile, pdf_bytes, mapping, submit=False, approved=False):
    output = DATA_DIR / 'automation' / str(uuid4())
    output.mkdir(parents=True)
    pdf_path = output / 'cv.pdf'
    pdf_path.write_bytes(pdf_bytes)
    request = {'url': url, 'profile': profile, 'pdf_path': str(pdf_path), 'mapping': mapping,
               'submit': submit, 'approved': approved}
    # A separate Python process keeps Playwright's Windows subprocess loop independent of Streamlit's event loop.
    try:
        process = subprocess.run([sys.executable, '-m', 'cvpilot.automation_worker'], input=json.dumps(request),
                                 text=True, capture_output=True, cwd=ROOT, timeout=100,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if process.returncode:
            return {'state': 'uncertain' if submit else 'failed', 'clicked': bool(submit),
                    'error': 'The browser worker failed. Review the target application before retrying.'}
        return json.loads(process.stdout)
    except subprocess.TimeoutExpired:
        return {'state': 'uncertain' if submit else 'failed', 'clicked': bool(submit),
                'error': 'The browser timed out. Submission outcome is unknown; do not retry without checking.'}
