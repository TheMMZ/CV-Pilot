"""One-time, read-only import of the previous local SQLite dataset into PostgreSQL."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from psycopg.types.json import Jsonb
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cvpilot import DATA_DIR
from cvpilot.storage import Store

def migrate():
    old_path = DATA_DIR / 'cv-pilot.sqlite'
    if not old_path.exists():
        print('No previous SQLite database found. PostgreSQL is ready for a fresh profile.')
        return
    store = Store()
    store.initialize()
    with sqlite3.connect(old_path.as_uri() + '?mode=ro', uri=True) as old, store.connect() as conn:
        if conn.execute("SELECT 1 FROM cv_settings WHERE key='legacy_import'").fetchone():
            print('Previous local data was already migrated. No data was overwritten.')
            return
        for key, value in old.execute('SELECT key,value FROM settings'):
            if key in ('profile', 'github'):
                conn.execute('INSERT INTO cv_settings VALUES(%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, Jsonb(json.loads(value))))
        count = 0
        for application_id, created, status, payload in old.execute('SELECT id,created,status,payload FROM applications'):
            conn.execute('INSERT INTO cv_applications(id,created,status,payload) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING', (application_id, created, status, Jsonb(json.loads(payload))))
            count += 1
        conn.execute('INSERT INTO cv_settings VALUES(%s,%s)', ('legacy_import', Jsonb({'at': datetime.now(timezone.utc).isoformat()})))
    print(f'Migrated saved profile, GitHub evidence, and {count} applications to PostgreSQL. Original database preserved.')

if __name__ == '__main__':
    migrate()
