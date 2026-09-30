import os
import secrets
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from database import UFS, connect, initialize

key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


@asynccontextmanager
async def lifespan(app):
    key = os.environ.get('API_KEY', '')
    if len(key.encode()) < 32:
        raise RuntimeError('Defina API_KEY com pelo menos 32 bytes antes de iniciar.')
    app.state.api_key = key.encode()
    initialize()
    yield


app = FastAPI(title='API de Feriados do Brasil', version='1.0.0', lifespan=lifespan)


def authorize(key: Annotated[str | None, Security(key_header)]):
    if key is None or not secrets.compare_digest(key.encode(), app.state.api_key):
        raise HTTPException(status_code=401, detail='Chave de API ausente ou inválida.')


def valid_uf(uf: str | None = None):
    if uf is None:
        return None
    uf = uf.strip().upper()
    if uf not in UFS:
        raise HTTPException(status_code=422, detail='UF inválida. Consulte /v1/estados.')
    return uf


class Feriado(BaseModel):
    data: date
    nome: str
    tipo: Literal['nacional', 'estadual']
    uf: str | None
    fonte: str
    versao_fonte: str
    atualizado_em: str


class ListaFeriados(BaseModel):
    ano: int
    uf: str | None
    total: int
    feriados: list[Feriado]


def query_holidays(year, uf=None, day=None):
    with connect() as db:
        if not db.execute('SELECT 1 FROM cargas WHERE ano = ?', (year,)).fetchone():
            raise HTTPException(status_code=409, detail=f'Ano {year} ainda não carregado. Execute seed.py para esse ano.')
        sql = 'SELECT * FROM feriados WHERE data BETWEEN ? AND ?'
        params = [f'{year}-01-01', f'{year}-12-31']
        if uf:
            sql += " AND (uf = '' OR uf = ?)"
            params.append(uf)
        if day:
            sql += ' AND data = ?'
            params.append(day.isoformat())
        rows = db.execute(sql + ' ORDER BY data, uf, nome', params).fetchall()
    return [dict(row) | {'uf': row['uf'] or None} for row in rows]


@app.get('/health')
def health():
    with connect() as db:
        loaded = db.execute('SELECT count(*) FROM cargas').fetchone()[0]
    if not loaded:
        raise HTTPException(status_code=503, detail='Banco sem carga de feriados.')
    return {'status': 'ok'}


@app.get('/v1/estados', dependencies=[Depends(authorize)])
def states():
    return {'ufs': UFS}


@app.get('/v1/cobertura', dependencies=[Depends(authorize)])
def coverage():
    with connect() as db:
        rows = db.execute('SELECT * FROM cargas ORDER BY ano').fetchall()
    return {'ufs': UFS, 'anos': [dict(row) for row in rows],
            'municipais_incluidos': False, 'pontos_facultativos_incluidos': False,
            'observacao': 'Base gerada pela biblioteca holidays; cobertura estadual sujeita à revisão das leis locais.'}


@app.get('/v1/feriados', response_model=ListaFeriados, dependencies=[Depends(authorize)])
def list_holidays(ano: Annotated[int, Query(ge=2000, le=2100)], uf: Annotated[str | None, Depends(valid_uf)]):
    rows = query_holidays(ano, uf)
    return {'ano': ano, 'uf': uf, 'total': len(rows), 'feriados': rows}


@app.get('/v1/feriados/verificar', dependencies=[Depends(authorize)])
def check_holiday(data: date, uf: Annotated[str, Query(min_length=2, max_length=2)]):
    normalized = valid_uf(uf)
    rows = query_holidays(data.year, normalized, data)
    return {'data': data, 'uf': normalized, 'feriado': bool(rows), 'feriados': rows,
            'escopo': 'nacional_e_estadual; não inclui feriados municipais'}
