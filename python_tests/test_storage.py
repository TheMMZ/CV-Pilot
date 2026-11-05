import os
from uuid import uuid4
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import psycopg
from psycopg import sql
import pytest
from cvpilot.storage import Store
from cvpilot.matching import tailor

@pytest.fixture
def store():
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        pytest.skip('DATABASE_URL required for real PostgreSQL integration tests')
    schema = 'test_cvpilot_' + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    parts = urlsplit(dsn)
    query = dict(parse_qsl(parts.query));query['options'] = '-csearch_path=' + schema
    isolated = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    db = Store(isolated)
    db.initialize()
    try:
        yield db
    finally:
        assert schema.startswith('test_cvpilot_')
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

def test_postgres_snapshots_and_submission_guard(store, profile, job):
    store.put('profile', profile)
    application_id = store.create_application(tailor(profile, [], job))
    changed = dict(profile, name='Changed candidate')
    store.put('profile', changed)
    assert store.application(application_id)['profile']['name'] == profile['name']
    store.set_status(application_id, 'Ready')
    store.claim_submission(application_id)
    with pytest.raises(ValueError):
        store.claim_submission(application_id)
    store.record_automation(application_id, {'state': 'submitted', 'clicked': True}, submitting=True)
    result = store.application(application_id)
    assert result['status'] == 'Applied' and result['submit_state'] == 'submitted'
    assert len(store.events(application_id)) == 1
