-- =====================================================================
-- Consultas de VALIDAÇÃO do banco de origem (rode no DBeaver, uma por vez: Ctrl+Enter)
-- =====================================================================

-- 1) Linhas por tabela
SELECT table_name AS tabela,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text::int AS linhas
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY linhas DESC;

-- 2) Distribuição de datas (últimos 3 anos)
SELECT 'ipca_valor' AS tabela, min(periodo) AS primeiro, max(periodo) AS ultimo, count(DISTINCT periodo) AS meses FROM ipca_valor
UNION ALL
SELECT 'inpc_valor', min(periodo), max(periodo), count(DISTINCT periodo) FROM inpc_valor;

SELECT 'populacao_municipio' AS tabela, ano, count(*) AS linhas FROM populacao_municipio GROUP BY ano
UNION ALL SELECT 'pib_municipio', ano, count(*) FROM pib_municipio GROUP BY ano
UNION ALL SELECT 'producao_agricola', ano, count(*) FROM producao_agricola GROUP BY ano
UNION ALL SELECT 'rebanho_municipio', ano, count(*) FROM rebanho_municipio GROUP BY ano
UNION ALL SELECT 'producao_origem_animal', ano, count(*) FROM producao_origem_animal GROUP BY ano
ORDER BY tabela, ano;

SELECT ano, trimestre, count(*) AS domicilios FROM pnad_domicilio GROUP BY ano, trimestre ORDER BY ano, trimestre;

-- 3) Níveis das categorias de produto (confere a classificação por nível)
SELECT nivel, count(*) FROM categoria_produto GROUP BY nivel ORDER BY nivel;

-- ---------------------------------------------------------------------
-- NORMALIZAÇÃO E INTEGRIDADE
-- ---------------------------------------------------------------------

-- 4) Tabelas SEM chave primária
SELECT t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints c
       ON c.table_schema = t.table_schema AND c.table_name = t.table_name
      AND c.constraint_type = 'PRIMARY KEY'
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE' AND c.constraint_name IS NULL;

-- 5) Chaves estrangeiras existentes
SELECT conrelid::regclass AS tabela_filha, a.attname AS coluna,
       confrelid::regclass AS tabela_pai, af.attname AS coluna_pai
FROM pg_constraint c
JOIN LATERAL unnest(c.conkey, c.confkey) AS k(attnum, fattnum) ON true
JOIN pg_attribute a  ON a.attrelid = c.conrelid  AND a.attnum = k.attnum
JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = k.fattnum
WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
ORDER BY 1, 2;

-- 6) Moradores sem domicílio e ocupações sem morador
SELECT (SELECT count(*) FROM pnad_morador m LEFT JOIN pnad_domicilio d ON d.domicilio_id = m.domicilio_id WHERE d.domicilio_id IS NULL) AS moradores_orfaos,
       (SELECT count(*) FROM pnad_ocupacao o LEFT JOIN pnad_morador m ON m.morador_id = o.morador_id WHERE m.morador_id IS NULL) AS ocupacoes_orfas;

-- 7) Amostra dos dados
SELECT * FROM municipio LIMIT 5;
SELECT * FROM pib_municipio LIMIT 5;
SELECT * FROM pnad_morador LIMIT 5;
