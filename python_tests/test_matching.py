from io import BytesIO
from pypdf import PdfReader
from cvpilot.matching import extract_skills, analyze, tailor
from cvpilot.documents import resume_pdf
from cvpilot.models import Job, Profile
from pydantic import ValidationError
import pytest

def test_word_boundaries():
    skills = extract_skills('JavaScript, PostgreSQL, C++ and Node.js')
    assert 'JavaScript' in skills and 'Java' not in skills
    assert 'C++' in skills and 'Node.js' in skills
    assert 'Express' not in extract_skills('expressive')

def test_planned_tools_are_not_experience(profile, job):
    result = analyze(profile, [], job)
    assert 'Snowflake' in result['missing'] and 'Airflow' in result['missing']
    assert any(m['skill'] == 'Python' for m in result['matched'])

def test_repository_evidence_is_reviewable(profile, job):
    repo = {'id': 1, 'name': 'snow', 'url': 'https://github.com/example/snow', 'description': 'Snowflake pipeline', 'readme': '', 'languages': [], 'verified': True, 'fork': True}
    assert 'Snowflake' in analyze(profile, [repo], job)['missing']
    repo['fork'] = False
    assert 'Snowflake' not in analyze(profile, [repo], job)['missing']

def test_tailoring_and_real_pdf_preserve_facts(profile, job):
    draft = tailor(profile, [], job)
    assert set(draft['profile']['skills']) == set(profile['skills'])
    assert draft['profile']['projects'][0]['status'] == 'planned'
    assert set(draft['profile']['experience'][0]['bullets']) == set(profile['experience'][0]['bullets'])
    pdf = resume_pdf(draft)
    assert pdf.startswith(b'%PDF-')
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert profile['name'] in text and 'planned' in text and 'Experience'.upper() in text

def test_no_requirements_is_unknown(profile):
    assert analyze(profile, [], {'title': 'Intern', 'description': 'Help the team.'})['score'] is None

def test_invalid_application_url(job):
    with pytest.raises(ValidationError):
        Job(**{**job, 'url': 'file:///etc/passwd'})
