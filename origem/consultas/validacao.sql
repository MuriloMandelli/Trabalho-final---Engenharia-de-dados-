-- =====================================================================
-- Consultas de VALIDAÇÃO do banco de origem (rode no DBeaver)
-- Guarde os resultados (print) para a documentação do projeto.
-- =====================================================================

-- 1) Quantidade de tabelas (requisito: mínimo 10)
SELECT count(*) AS qtd_tabelas
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- 2) Linhas por tabela (requisito: 10.000+ nas tabelas principais)
SELECT 'regiao' AS tabela, count(*) AS linhas FROM regiao
UNION ALL SELECT 'uf', count(*) FROM uf
UNION ALL SELECT 'mesorregiao', count(*) FROM mesorregiao
UNION ALL SELECT 'microrregiao', count(*) FROM microrregiao
UNION ALL SELECT 'municipio', count(*) FROM municipio
UNION ALL SELECT 'distrito', count(*) FROM distrito
UNION ALL SELECT 'area_ipca', count(*) FROM area_ipca
UNION ALL SELECT 'categoria_produto', count(*) FROM categoria_produto
UNION ALL SELECT 'ipca_valor', count(*) FROM ipca_valor
UNION ALL SELECT 'inpc_valor', count(*) FROM inpc_valor
UNION ALL SELECT 'populacao_municipio', count(*) FROM populacao_municipio
ORDER BY linhas DESC;

-- 3) Distribuição de datas nos últimos 3 anos (requisito: 36 meses)
SELECT 'ipca_valor' AS tabela, min(periodo) AS primeiro_mes, max(periodo) AS ultimo_mes,
       count(DISTINCT periodo) AS meses
FROM ipca_valor
UNION ALL
SELECT 'inpc_valor', min(periodo), max(periodo), count(DISTINCT periodo) FROM inpc_valor;

-- 4) Anos de população carregados
SELECT ano, count(*) AS municipios FROM populacao_municipio GROUP BY ano ORDER BY ano;

-- 5) Níveis das categorias de produto (confere se a classificação por nível fez sentido)
SELECT nivel, count(*) FROM categoria_produto GROUP BY nivel ORDER BY nivel;

-- ---------------------------------------------------------------------
-- NORMALIZAÇÃO
-- ---------------------------------------------------------------------

-- 6) Tabelas SEM chave primária (esperado: nenhuma linha)
SELECT t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints c
       ON c.table_schema = t.table_schema AND c.table_name = t.table_name
      AND c.constraint_type = 'PRIMARY KEY'
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE' AND c.constraint_name IS NULL;

-- 7) Chaves estrangeiras existentes (documente o resultado)
SELECT tc.table_name AS tabela_filha, kcu.column_name AS coluna,
       ccu.table_name AS tabela_pai, ccu.column_name AS coluna_pai
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
ORDER BY tabela_filha, coluna;

-- 8) Linhas "órfãs" nos fatos (esperado: 0 em todas)
SELECT 'ipca sem area' AS teste, count(*) FROM ipca_valor f LEFT JOIN area_ipca a ON a.id = f.area_id WHERE a.id IS NULL
UNION ALL SELECT 'ipca sem categoria', count(*) FROM ipca_valor f LEFT JOIN categoria_produto c ON c.id = f.categoria_id WHERE c.id IS NULL
UNION ALL SELECT 'inpc sem area', count(*) FROM inpc_valor f LEFT JOIN area_ipca a ON a.id = f.area_id WHERE a.id IS NULL
UNION ALL SELECT 'populacao sem municipio', count(*) FROM populacao_municipio f LEFT JOIN municipio m ON m.id = f.municipio_id WHERE m.id IS NULL;

-- 9) Duplicidade de negócio (esperado: nenhuma linha)
SELECT area_id, categoria_id, periodo, count(*)
FROM ipca_valor GROUP BY area_id, categoria_id, periodo HAVING count(*) > 1;

-- 10) Municípios sem microrregião (informativo: pode haver alguns)
SELECT count(*) AS municipios_sem_microrregiao FROM municipio WHERE microrregiao_id IS NULL;
