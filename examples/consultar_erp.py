"""Exemplo independente de biblioteca externa. Defina API_KEY e opcionalmente API_URL."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def consultar(ano, uf):
    url = os.environ.get('API_URL', 'http://127.0.0.1:8000').rstrip('/')
    request = Request(f'{url}/v1/feriados?{urlencode({"ano": ano, "uf": uf})}',
                      headers={'X-API-Key': os.environ['API_KEY']})
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError('Falha ao consultar feriados. Não presumir dia útil.') from error


if __name__ == '__main__':
    print(json.dumps(consultar(2026, 'SP'), ensure_ascii=False, indent=2))
