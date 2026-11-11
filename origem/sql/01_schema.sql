-- =====================================================================
-- Banco de ORIGEM - dados do IBGE (localidades, IPCA, INPC, população)
-- 11 tabelas: 8 dimensões + 3 fatos (+ ipca_valor e inpc_valor são as principais)
-- =====================================================================

-- ---------- Dimensões geográficas (API de Localidades) ----------
CREATE TABLE regiao (
    id            INT PRIMARY KEY,
    sigla         VARCHAR(5)   NOT NULL,
    nome          VARCHAR(50)  NOT NULL,
    atualizado_em TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE uf (
    id            INT PRIMARY KEY,
    sigla         CHAR(2)      NOT NULL,
    nome          VARCHAR(50)  NOT NULL,
    regiao_id     INT          NOT NULL REFERENCES regiao(id),
    atualizado_em TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE mesorregiao (
    id            INT PRIMARY KEY,
    nome          VARCHAR(100) NOT NULL,
    uf_id         INT          NOT NULL REFERENCES uf(id),
    atualizado_em TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE microrregiao (
    id             INT PRIMARY KEY,
    nome           VARCHAR(100) NOT NULL,
    mesorregiao_id INT          NOT NULL REFERENCES mesorregiao(id),
    atualizado_em  TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE municipio (
    id              INT PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL,
    microrregiao_id INT REFERENCES microrregiao(id),  -- pode ser nulo para municípios sem microrregião na API
    atualizado_em   TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE distrito (
    id            INT PRIMARY KEY,
    nome          VARCHAR(100) NOT NULL,
    municipio_id  INT          NOT NULL REFERENCES municipio(id),
    atualizado_em TIMESTAMP    NOT NULL DEFAULT now()
);

-- ---------- Dimensões de preços (API de Agregados: IPCA e INPC) ----------
CREATE TABLE area_ipca (
    id            INT PRIMARY KEY,           -- código da localidade no IBGE
    nome          VARCHAR(100) NOT NULL,
    nivel         VARCHAR(50)  NOT NULL,     -- Brasil, Região Metropolitana ou Município
    atualizado_em TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE categoria_produto (
    id            INT PRIMARY KEY,           -- código da categoria no IBGE
    nome          VARCHAR(250) NOT NULL,
    nivel         VARCHAR(20)  NOT NULL,     -- geral, grupo, subgrupo, item, subitem
    atualizado_em TIMESTAMP    NOT NULL DEFAULT now()
);

-- ---------- Fatos ----------
CREATE TABLE ipca_valor (
    area_id         INT  NOT NULL REFERENCES area_ipca(id),
    categoria_id    INT  NOT NULL REFERENCES categoria_produto(id),
    periodo         DATE NOT NULL,           -- primeiro dia do mês de referência
    variacao_mensal NUMERIC(12,4),
    acumulado_ano   NUMERIC(12,4),
    acumulado_12m   NUMERIC(12,4),
    peso_mensal     NUMERIC(12,4),
    atualizado_em   TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (area_id, categoria_id, periodo)
);

CREATE TABLE inpc_valor (
    area_id         INT  NOT NULL REFERENCES area_ipca(id),
    categoria_id    INT  NOT NULL REFERENCES categoria_produto(id),
    periodo         DATE NOT NULL,
    variacao_mensal NUMERIC(12,4),
    acumulado_ano   NUMERIC(12,4),
    acumulado_12m   NUMERIC(12,4),
    peso_mensal     NUMERIC(12,4),
    atualizado_em   TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (area_id, categoria_id, periodo)
);

CREATE TABLE populacao_municipio (
    municipio_id  INT NOT NULL REFERENCES municipio(id),
    ano           INT NOT NULL,
    populacao     INT,
    atualizado_em TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (municipio_id, ano)
);

CREATE INDEX idx_ipca_periodo ON ipca_valor(periodo);
CREATE INDEX idx_inpc_periodo ON inpc_valor(periodo);

-- ---------- Gatilho: atualiza "atualizado_em" sempre que uma linha é alterada ----------
-- (usado pelo pipeline para detectar mudanças: carga incremental e SCD tipo 2)
CREATE OR REPLACE FUNCTION set_atualizado_em() RETURNS trigger AS $$
BEGIN
    NEW.atualizado_em = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'regiao','uf','mesorregiao','microrregiao','municipio','distrito',
        'area_ipca','categoria_produto','ipca_valor','inpc_valor','populacao_municipio'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%I_atualizado BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_atualizado_em()', t, t);
    END LOOP;
END $$;
