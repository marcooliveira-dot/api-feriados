"""Carga transacional, repetível, de feriados nacionais e estaduais."""
import argparse
from datetime import datetime, timezone

import holidays

from database import UFS, connect, initialize

SOURCE = 'https://holidays.readthedocs.io/en/latest/auto_gen_docs/brazil/'


def entries(calendar):
    return {(day.isoformat(), name) for day in calendar for name in calendar.get_list(day)}


def seed(start, end, path=None):
    if not 2000 <= start <= end <= 2100:
        raise ValueError('Informe anos entre 2000 e 2100, em ordem crescente.')
    initialize(path)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for year in range(start, end + 1):
        national = entries(holidays.country_holidays('BR', years=year, language='pt_BR', observed=False))
        # Lei 9.093/1995, art. 2: a Sexta-feira da Paixão exige lei municipal.
        # Preservamos national completo para não reclassificar essa data como estadual.
        for day, name in sorted(national):
            if name != 'Sexta-feira Santa':
                rows.append((day, name, 'nacional', '', SOURCE, holidays.__version__, now))
        for uf in UFS:
            regional = entries(holidays.country_holidays('BR', subdiv=uf, years=year, language='pt_BR', observed=False))
            for day, name in sorted(regional - national):
                rows.append((day, name, 'estadual', uf, SOURCE, holidays.__version__, now))
    with connect(path) as db:
        # Substitui apenas a carga gerenciada dos anos solicitados, em uma transação.
        db.execute('DELETE FROM feriados WHERE data BETWEEN ? AND ? AND fonte = ?',
                   (f'{start}-01-01', f'{end}-12-31', SOURCE))
        db.executemany('INSERT INTO feriados VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
        db.executemany('INSERT OR REPLACE INTO cargas VALUES (?, ?, ?)',
                       [(year, holidays.__version__, now) for year in range(start, end + 1)])
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inicio', type=int, default=2026)
    parser.add_argument('--fim', type=int, default=2030)
    args = parser.parse_args()
    print(f'{seed(args.inicio, args.fim)} feriados carregados.')
