import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UFS = tuple('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split())


def database_path():
    return Path(os.environ.get('DATABASE_PATH', str(ROOT / 'data' / 'feriados.sqlite3'))).resolve()


@contextmanager
def connect(path=None):
    target = Path(path) if path else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path=None):
    with connect(path) as db:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError('Versão de banco incompatível.')
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript((ROOT / 'schema.sql').read_text())
