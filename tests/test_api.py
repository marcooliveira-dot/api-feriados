import pytest
from fastapi.testclient import TestClient

from app import app
from database import UFS, connect
from seed import seed

KEY = 'chave-exclusiva-dos-testes-0123456789'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('API_KEY', KEY)
    seed(2026, 2026)
    with TestClient(app) as client:
        client.headers['X-API-Key'] = KEY
        yield client


def test_auth(client):
    assert client.get('/v1/feriados?ano=2026', headers={'X-API-Key': 'errada'}).status_code == 401
    del client.headers['X-API-Key']
    assert client.get('/v1/feriados?ano=2026').status_code == 401


@pytest.mark.parametrize('uf', UFS)
def test_all_states(client, uf):
    response = client.get('/v1/feriados', params={'ano': 2026, 'uf': uf})
    assert response.status_code == 200
    rows = response.json()['feriados']
    assert any(row['data'] == '2026-01-01' and row['tipo'] == 'nacional' for row in rows)
    assert all(row['uf'] in (None, uf) for row in rows)


def test_sp_isolation_and_normalization(client):
    sp = client.get('/v1/feriados?ano=2026&uf=sp').json()
    rj = client.get('/v1/feriados?ano=2026&uf=RJ').json()
    assert sp['uf'] == 'SP'
    assert any(row['data'] == '2026-07-09' and row['tipo'] == 'estadual' for row in sp['feriados'])
    assert not any(row['uf'] == 'SP' for row in rj['feriados'])


def test_no_municipal_or_optional_as_national(client):
    rows = client.get('/v1/feriados?ano=2026&uf=SP').json()['feriados']
    assert not any(row['data'] in ('2026-04-03', '2026-02-17', '2026-06-04') for row in rows)
    assert any(row['data'] == '2026-11-20' and row['tipo'] == 'nacional' for row in rows)


@pytest.mark.parametrize('query', ['ano=2026&uf=XX', 'ano=abc', 'ano=1999', 'ano=2101', 'ano=2026&uf='])
def test_validation(client, query):
    assert client.get('/v1/feriados?' + query).status_code == 422


def test_unloaded_year_is_not_empty_calendar(client):
    assert client.get('/v1/feriados?ano=2027').status_code == 409


def test_check_date(client):
    assert client.get('/v1/feriados/verificar?data=2026-07-09&uf=SP').json()['feriado'] is True
    assert client.get('/v1/feriados/verificar?data=2026-07-09&uf=RJ').json()['feriado'] is False
    assert client.get('/v1/feriados/verificar?data=2026-02-30&uf=SP').status_code == 422
    assert client.get('/v1/feriados/verificar?data=2026-01-01').status_code == 422


def test_reload_preserves_other_years(client):
    before = client.get('/v1/feriados?ano=2026').json()['total']
    seed(2026, 2027)
    seed(2026, 2026)
    assert client.get('/v1/feriados?ano=2026').json()['total'] == before
    assert client.get('/v1/feriados?ano=2027').status_code == 200
    with connect() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_missing_key_fails_startup(monkeypatch, tmp_path):
    monkeypatch.delenv('API_KEY', raising=False)
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'empty.sqlite3'))
    with pytest.raises(RuntimeError, match='API_KEY'):
        with TestClient(app):
            pass


def test_empty_database_not_ready(monkeypatch, tmp_path):
    monkeypatch.setenv('API_KEY', KEY)
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'empty.sqlite3'))
    with TestClient(app) as client:
        assert client.get('/health').status_code == 503
