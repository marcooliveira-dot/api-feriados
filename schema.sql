CREATE TABLE IF NOT EXISTS feriados (
    data TEXT NOT NULL,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('nacional', 'estadual')),
    uf TEXT NOT NULL,
    fonte TEXT NOT NULL,
    versao_fonte TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY(data, nome, uf),
    CHECK((tipo = 'nacional' AND uf = '') OR (tipo = 'estadual' AND length(uf) = 2))
);
CREATE INDEX IF NOT EXISTS idx_feriados_uf_data ON feriados(uf, data);
CREATE TABLE IF NOT EXISTS cargas (
    ano INTEGER PRIMARY KEY,
    versao_fonte TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);
PRAGMA user_version = 1;
