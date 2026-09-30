import argparse
import sqlite3
from pathlib import Path

from database import database_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backup consistente do SQLite, inclusive com WAL ativo.')
    parser.add_argument('destino', type=Path)
    args = parser.parse_args()
    target = args.destino.resolve()
    if target.exists():
        parser.error('O destino já existe; escolha outro arquivo para preservar o backup anterior.')
    target.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(database_path().as_uri() + '?mode=ro', uri=True)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    print(f'Backup salvo em {target}')
