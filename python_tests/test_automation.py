from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import pytest
from cvpilot.automation import fill_application
from cvpilot.documents import resume_pdf
from cvpilot.matching import tailor

FORM = b'''<!doctype html><html><body><h1>Local application fixture</h1><form method="post" enctype="multipart/form-data"><label>Full name<input name="name" required></label><label>Email<input type="email" name="email" required></label><label>Resume<input type="file" name="resume" required></label><button type="submit">Apply</button></form></body></html>'''

@pytest.fixture
def form_server():
    submissions = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200);self.send_header('Content-Type', 'text/html');self.end_headers();self.wfile.write(FORM)
        def do_POST(self):
            submissions.append(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(200);self.send_header('Content-Type', 'text/html');self.end_headers();self.wfile.write(b'<h1>Thank you for applying</h1>')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True);thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', submissions
    finally:
        server.shutdown();server.server_close()

def test_playwright_preview_and_approved_submission(form_server, profile, job, tmp_path):
    url, submissions = form_server
    mapping = {'fields': {'name': 'Full name', 'email': 'Email'}, 'resume_label': 'Resume',
               'submit_selector': 'button[type=submit]', 'confirmation_text': 'Thank you for applying'}
    pdf = resume_pdf(tailor(profile, [], job))
    preview = fill_application(url, profile, pdf, mapping, allow_local=True, output_dir=tmp_path / 'preview')
    assert preview['state'] == 'prepared', preview
    assert not submissions
    with pytest.raises(ValueError, match='approve'):
        fill_application(url, profile, pdf, mapping, submit=True, approved=False, allow_local=True)
    submitted = fill_application(url, profile, pdf, mapping, submit=True, approved=True, allow_local=True, output_dir=tmp_path / 'submitted')
    assert submitted['state'] == 'submitted', submitted
    assert len(submissions) == 1
    assert b'%PDF-' in submissions[0] and profile['email'].encode() in submissions[0]
