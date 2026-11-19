-- =====================================================================
-- Banco de ORIGEM - dados reais do IBGE
-- Tabelas criadas aqui: municipio, categoria_produto, ipca_valor, inpc_valor,
--   populacao_municipio, pnad_domicilio, pnad_morador, pnad_ocupacao.
-- Criadas pelos scripts de carga (a partir do dicionário do IBGE):
--   pib_municipio, producao_agricola, rebanho_municipio, producao_origem_animal.
-- =====================================================================

-- ---------- Gatilho: atualiza "atualizado_em" sempre que uma linha é alterada ----------
-- (usado pelo pipeline para detectar mudanças: carga incremental e SCD tipo 2)
CREATE OR REPLACE FUNCTION set_atualizado_em() RETURNS trigger AS $$
BEGIN
    NEW.atualizado_em = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------- Município (hierarquia geográfica achatada em colunas) ----------
CREATE TABLE municipio (
    id                         INT PRIMARY KEY,          -- código IBGE de 7 dígitos
    nome                       VARCHAR(120) NOT NULL,
    microrregiao_id            INT,
    microrregiao_nome          VARCHAR(120),
    mesorregiao_id             INT,
    mesorregiao_nome           VARCHAR(120),
    uf_id                      INT,
    uf_sigla                   CHAR(2),
    uf_nome                    VARCHAR(60),
    regiao_id                  INT,
    regiao_sigla               VARCHAR(5),
    regiao_nome                VARCHAR(30),
    regiao_imediata_id         INT,
    regiao_imediata_nome       VARCHAR(120),
    regiao_intermediaria_id    INT,
    regiao_intermediaria_nome  VARCHAR(120),
    atualizado_em              TIMESTAMP NOT NULL DEFAULT now()
);

-- ---------- Produtos e serviços medidos pelo IPCA/INPC ----------
CREATE TABLE categoria_produto (
    id            INT PRIMARY KEY,           -- código da categoria no IBGE (SIDRA)
    codigo        VARCHAR(20),               -- ex.: 1101002
    descricao     VARCHAR(300),              -- ex.: Arroz
    nome          VARCHAR(300) NOT NULL,     -- texto original: 1101002.Arroz
    nivel         VARCHAR(20)  NOT NULL,     -- geral, grupo, subgrupo, item, subitem
    atualizado_em TIMESTAMP NOT NULL DEFAULT now()
);

-- ---------- Fatos de preços (IPCA e INPC) ----------
CREATE TABLE ipca_valor (
    localidade_id   INT          NOT NULL,   -- 1 = Brasil
    localidade_nome VARCHAR(100) NOT NULL,
    categoria_id    INT          NOT NULL REFERENCES categoria_produto(id),
    periodo         DATE         NOT NULL,   -- primeiro dia do mês de referência
    variacao_mensal NUMERIC(12,4),
    acumulado_ano   NUMERIC(12,4),
    acumulado_12m   NUMERIC(12,4),
    peso_mensal     NUMERIC(12,4),
    atualizado_em   TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (localidade_id, categoria_id, periodo)
);

CREATE TABLE inpc_valor (
    localidade_id   INT          NOT NULL,
    localidade_nome VARCHAR(100) NOT NULL,
    categoria_id    INT          NOT NULL REFERENCES categoria_produto(id),
    periodo         DATE         NOT NULL,
    variacao_mensal NUMERIC(12,4),
    acumulado_ano   NUMERIC(12,4),
    acumulado_12m   NUMERIC(12,4),
    peso_mensal     NUMERIC(12,4),
    atualizado_em   TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (localidade_id, categoria_id, periodo)
);

CREATE INDEX idx_ipca_periodo ON ipca_valor(periodo);
CREATE INDEX idx_inpc_periodo ON inpc_valor(periodo);

-- ---------- População estimada por município ----------
CREATE TABLE populacao_municipio (
    municipio_id  INT NOT NULL REFERENCES municipio(id),
    ano           INT NOT NULL,
    populacao     INT,
    atualizado_em TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (municipio_id, ano)
);

-- ---------- PNAD Contínua: respostas dos questionários (microdados), normalizadas ----------
-- Domicílio -> Morador -> Ocupação. Nome da coluna = variável do dicionário do IBGE (em minúsculas).
CREATE TABLE pnad_domicilio (
    domicilio_id VARCHAR(40) PRIMARY KEY,    -- ano+trimestre_UPA_V1008_V1014
    ano        INTEGER , -- ano de referência
    trimestre  INTEGER , -- trimestre de referência
    uf         TEXT    , -- código da unidade da federação
    capital    TEXT    , -- município da capital
    rm_ride    TEXT    , -- região metropolitana / RIDE
    upa        TEXT    , -- unidade primária de amostragem
    estrato    TEXT    , -- estrato de amostragem
    v1008      TEXT    , -- número de seleção do domicílio
    v1014      TEXT    , -- painel (grupo de rotação)
    v1022      TEXT    , -- situação do domicílio (urbana/rural)
    v1023      TEXT    , -- tipo de área (capital, resto da RM, resto da UF)
    v2001      INTEGER , -- número de pessoas no domicílio
    atualizado_em TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pnad_morador (
    morador_id   VARCHAR(60) PRIMARY KEY,    -- domicilio_id + número de ordem
    domicilio_id VARCHAR(40) NOT NULL REFERENCES pnad_domicilio(domicilio_id),
    v2003      INTEGER , -- número de ordem da pessoa no domicílio
    v2005      TEXT    , -- condição no domicílio
    v2007      TEXT    , -- sexo
    v2009      INTEGER , -- idade na data de referência
    v2010      TEXT    , -- cor ou raça
    v3001      TEXT    , -- sabe ler e escrever
    v3002      TEXT    , -- frequenta escola
    v3009a     TEXT    , -- curso mais elevado que frequentou
    vd3004     TEXT    , -- nível de instrução mais elevado
    vd3005     INTEGER , -- anos de estudo
    vd4001     TEXT    , -- condição na força de trabalho
    vd4002     TEXT    , -- condição de ocupação
    v1027      NUMERIC , -- peso sem pós-estratificação
    v1028      NUMERIC , -- peso com pós-estratificação
    v1029      NUMERIC , -- projeção da população
    atualizado_em TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pnad_ocupacao (
    morador_id   VARCHAR(60) PRIMARY KEY REFERENCES pnad_morador(morador_id),
    v4009      INTEGER , -- quantidade de trabalhos
    v4010      TEXT    , -- código da ocupação do trabalho principal
    v4012      TEXT    , -- posição na ocupação
    v4013      TEXT    , -- código da atividade (CNAE-Domiciliar)
    v4029      TEXT    , -- carteira de trabalho assinada
    v4032      TEXT    , -- contribui para instituto de previdência
    v4039      INTEGER , -- horas habitualmente trabalhadas no trabalho principal
    vd4009     TEXT    , -- posição na ocupação e categoria do emprego
    vd4010     TEXT    , -- grupamento de atividade do trabalho principal
    vd4011     TEXT    , -- grupamento ocupacional do trabalho principal
    vd4012     TEXT    , -- contribuição para previdência (derivada)
    vd4016     NUMERIC , -- rendimento habitual do trabalho principal
    vd4017     NUMERIC , -- rendimento efetivo do trabalho principal
    vd4019     NUMERIC , -- rendimento habitual de todos os trabalhos
    vd4020     NUMERIC , -- rendimento efetivo de todos os trabalhos
    vd4031     INTEGER , -- horas habituais em todos os trabalhos
    atualizado_em TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_pnad_morador_domicilio ON pnad_morador(domicilio_id);

-- ---------- Gatilhos de atualizado_em nas tabelas acima ----------
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'municipio','categoria_produto','ipca_valor','inpc_valor','populacao_municipio',
        'pnad_domicilio','pnad_morador','pnad_ocupacao'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%I_atualizado BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_atualizado_em()', t, t);
    END LOOP;
END $$;
