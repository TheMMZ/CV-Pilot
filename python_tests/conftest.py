import json
import pytest
from pathlib import Path

@pytest.fixture
def profile():
    return json.loads((Path(__file__).parent / 'fixtures' / 'profile.json').read_text(encoding='utf-8-sig'))

@pytest.fixture
def job():
    return {'title': 'Data Engineering Intern', 'company': 'Example company',
            'description': 'Build Python and PostgreSQL data pipelines with Docker. Snowflake and Airflow are desirable.', 'url': ''}
