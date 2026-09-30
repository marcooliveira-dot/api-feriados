# API de feriados do Brasil — SQLite

API HTTP/JSON em Python com banco SQLite separado, pronta para um ERP consumir. Consulta feriados nacionais e estaduais por ano e UF, com autenticação pelo cabeçalho `X-API-Key`. O código do ERP ainda não foi fornecido: a integração específica e a homologação no ERP estão pendentes.

## Início rápido

Requer Python 3.13. Execute na pasta deste projeto, em macOS ou Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python seed.py --inicio 2026 --fim 2030
export API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

No Windows PowerShell, ative com `.venv\Scripts\Activate.ps1` e configure a chave com `$env:API_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"`.

Guarde a chave no gerenciador de segredos do servidor e configure o mesmo valor no ERP. A chave gerada acima só existe na sessão atual do terminal. A API recusa iniciar sem chave de pelo menos 32 bytes. O arquivo `.env.example` documenta as variáveis: o comando Python não carrega `.env` automaticamente. Configure `DATABASE_PATH` se quiser outro caminho; o padrão é `data/feriados.sqlite3` ao lado do código.

Acesse http://127.0.0.1:8000/docs para a documentação interativa, clique em **Authorize** e informe a chave. O contrato OpenAPI está em `/openapi.json` e também em `openapi.json` no projeto.

## Consultas do ERP

```sh
curl --fail-with-body \
  -H "X-API-Key: $API_KEY" \
  'http://127.0.0.1:8000/v1/feriados?ano=2026&uf=SP'
```

| Rota | Resultado |
| --- | --- |
| `/v1/feriados?ano=2026&uf=SP` | Nacionais e estaduais de SP |
| `/v1/feriados?ano=2026` | Nacionais uma vez e estaduais de todas as UFs |
| `/v1/feriados/verificar?data=2026-07-09&uf=SP` | Verifica a data para a UF informada |
| `/v1/estados` | As 27 UFs, incluindo DF |
| `/v1/cobertura` | Anos carregados, origem e limitações |
| `/health` | Prontidão do banco, sem autenticação |

As datas usam `AAAA-MM-DD`. Feriados nacionais retornam `uf: null`; estaduais retornam a sigla. O resultado contém nome, tipo, fonte, versão da fonte e momento da carga. Sem UF, a listagem serve para exportar o cadastro inteiro, não para decidir se uma data é feriado em uma filial específica.

HTTP 401: chave incorreta ou ausente. HTTP 422: entrada inválida. HTTP 409: ano ainda não carregado; não trate isso como ausência de feriados. `/health` retorna 503 quando não há carga. O ERP deve tratar falhas e usar timeout; nunca converter erro de consulta em dia útil. Há um exemplo Python em `examples/consultar_erp.py`, com timeout e tratamento explícito de erros.

## SQLite e carga de dados

O pacote ZIP entregue inclui `data/feriados.sqlite3` com os anos de 2026 a 2030. No GitHub o banco é ignorado: gere-o com `seed.py`. O arquivo `schema.sql` cria as tabelas `feriados` e `cargas`, e os índices. Use um banco dedicado à API; não aponte para o banco existente do ERP sem adaptar o esquema e testar a migração.

```sh
python seed.py --inicio 2031 --fim 2031
```

A carga aceita 2000–2100, substitui os registros gerenciados pela fonte nos anos solicitados e preserva outros anos. Reexecutar não duplica registros. Substituição e metadados são gravados em uma transação. A API não consulta provedores externos a cada requisição; lê o SQLite local.

`schema.sql` é o esquema inicial v1, não um mecanismo de migrações futuras. Faça backup antes de trocar o esquema ou atualizar a fonte. Com a API em execução, use a API de backup do SQLite em vez de copiar somente o arquivo principal, pois o banco usa WAL. `backup.py destino.sqlite3` faz esse backup consistente.

## Origem e limites dos feriados

Dados gerados por [python-holidays, Brasil](https://holidays.readthedocs.io/en/latest/auto_gen_docs/brazil/), versão fixada em `requirements.txt`. As 27 UFs são consultáveis, mas isso não equivale a uma auditoria jurídica completa de todos os feriados estaduais. As regras estaduais provêm da biblioteca e devem ser homologadas com o calendário aplicável ao ERP antes do uso operacional. Alterações legais posteriores à versão da biblioteca e feriados extraordinários podem faltar. Anos futuros são projeções dessas regras, não calendários oficialmente publicados.

Pontos facultativos e feriados municipais não estão incluídos. A Sexta-feira Santa foi removida da base nacional da biblioteca por depender de lei municipal, conforme [Lei 9.093/1995, art. 2](https://www.planalto.gov.br/ccivil_03/leis/l9093.htm). O resultado `feriado: false` se refere apenas ao cadastro nacional/estadual disponível; não afirma que a data é dia útil no município ou no calendário bancário. Para cálculos de vencimentos por filial, será necessário incluir a cidade e as regras do ERP.

Para atualizar a base, revise a nova versão de `holidays`, atualize a dependência fixada, rode os testes e execute novamente a carga dos anos usados. A atualização não é automática.

## Servidor

Para produção, execute em um servidor com armazenamento persistente local e configure HTTPS no proxy de entrada. Ajuste o host do Uvicorn para a interface desejada e libere acesso apenas à rede necessária ao ERP. Não compartilhe o SQLite por pasta de rede entre vários servidores. O GitHub armazena o código e executa testes; GitHub Pages não executa esta API Python.

Alternativamente, há `Dockerfile` e `compose.yaml`:

```sh
cp .env.example .env
# Preencha API_KEY no .env com uma chave aleatória de pelo menos 32 bytes.
docker compose up --build -d
```

O Compose guarda o banco no volume `feriados_data` e publica a porta apenas em `127.0.0.1:8000`. Coloque o proxy HTTPS na mesma máquina. A carga inicial ocorre ao iniciar o contêiner; os anos padrão são 2026–2030. O contêiner foi preparado, mas sua execução depende de Docker e não foi validada neste ambiente.

## Testes e GitHub

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

O workflow `.github/workflows/tests.yml` executa os testes a cada push e pull request. `.gitignore` exclui chaves, ambientes virtuais e bancos. Repositório privado: https://github.com/marcooliveira-dot/api-feriados. Não há credenciais embutidas no código.

Após criar um repositório vazio na conta correta, é possível publicar usando Git ou GitHub Desktop. Os comandos abaixo pressupõem Git configurado e um repositório vazio; substitua a URL pela URL real:

```sh
git init -b main
git add .
git commit -m "Adiciona API de feriados com SQLite"
git remote add origin https://github.com/SEU_USUARIO/api-feriados.git
git push -u origin main
```
