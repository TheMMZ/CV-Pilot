import json
import os
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from . import ROOT
from .models import Profile

STATUSES = ['Draft', 'Ready', 'Applied', 'Interview', 'Rejected', 'Offer']

class Store:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv('DATABASE_URL', '')
        if not self.dsn.startswith(('postgresql://', 'postgres://')):
            raise RuntimeError('Set DATABASE_URL to a PostgreSQL connection URL in .env.')

    def connect(self):
        return psycopg.connect(self.dsn, connect_timeout=5, row_factory=dict_row)

    def initialize(self):
        with self.connect() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS cv_settings (key TEXT PRIMARY KEY, value JSONB NOT NULL);
                CREATE TABLE IF NOT EXISTS cv_applications (
                  id UUID PRIMARY KEY, created TIMESTAMPTZ NOT NULL DEFAULT now(),
                  status TEXT NOT NULL DEFAULT 'Draft', payload JSONB NOT NULL,
                  submit_state TEXT NOT NULL DEFAULT 'idle');
                CREATE TABLE IF NOT EXISTS cv_events (
                  id BIGSERIAL PRIMARY KEY, application_id UUID REFERENCES cv_applications(id),
                  created TIMESTAMPTZ NOT NULL DEFAULT now(), event TEXT NOT NULL, details JSONB NOT NULL);''')
            seed = ROOT / os.getenv('PROFILE_FILE', 'profile.seed.json')
            if not seed.exists():
                seed = ROOT / 'profile.example.json'
            profile = Profile.model_validate_json(seed.read_text(encoding='utf-8-sig')).model_dump()
            conn.execute('INSERT INTO cv_settings VALUES (%s, %s) ON CONFLICT DO NOTHING', ('profile', Jsonb(profile)))

    def get(self, key, default=None):
        with self.connect() as conn:
            row = conn.execute('SELECT value FROM cv_settings WHERE key=%s', (key,)).fetchone()
        return row['value'] if row else default

    def put(self, key, value):
        if key == 'profile':
            value = Profile.model_validate(value).model_dump()
        with self.connect() as conn:
            conn.execute('INSERT INTO cv_settings VALUES (%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, Jsonb(value)))

    def create_application(self, draft):
        application_id = str(uuid4())
        with self.connect() as conn:
            conn.execute('INSERT INTO cv_applications(id,payload) VALUES(%s,%s)', (application_id, Jsonb(draft)))
        return application_id

    def applications(self):
        with self.connect() as conn:
            rows = conn.execute('SELECT * FROM cv_applications ORDER BY created DESC').fetchall()
        return [self._application(r) for r in rows]

    def application(self, application_id):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM cv_applications WHERE id=%s', (application_id,)).fetchone()
        if not row:
            raise ValueError('Application not found.')
        return self._application(row)

    @staticmethod
    def _application(row):
        return {**row['payload'], 'id': str(row['id']), 'status': row['status'],
                'created': row['created'].isoformat(), 'submit_state': row['submit_state']}

    def set_status(self, application_id, status):
        if status not in STATUSES:
            raise ValueError('Unknown application status.')
        with self.connect() as conn:
            conn.execute('UPDATE cv_applications SET status=%s WHERE id=%s', (status, application_id))

    def claim_submission(self, application_id):
        with self.connect() as conn:
            row = conn.execute("UPDATE cv_applications SET submit_state='submitting' WHERE id=%s AND submit_state='idle' AND status NOT IN ('Applied','Interview','Offer') RETURNING id", (application_id,)).fetchone()
            if not row:
                raise ValueError('This application was submitted or has an unresolved submission. Review its history before retrying.')

    def record_automation(self, application_id, result, submitting=False):
        with self.connect() as conn:
            conn.execute('INSERT INTO cv_events(application_id,event,details) VALUES(%s,%s,%s)', (application_id, result['state'], Jsonb(result)))
            if submitting:
                state = 'submitted' if result['state'] == 'submitted' else 'uncertain' if result.get('clicked') else 'idle'
                conn.execute("UPDATE cv_applications SET submit_state=%s, status=CASE WHEN %s='submitted' THEN 'Applied' ELSE status END WHERE id=%s", (state, result['state'], application_id))

    def events(self, application_id):
        with self.connect() as conn:
            return conn.execute('SELECT event,created,details FROM cv_events WHERE application_id=%s ORDER BY created DESC', (application_id,)).fetchall()
