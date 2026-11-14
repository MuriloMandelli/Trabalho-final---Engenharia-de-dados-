## TODO - Ese arquivo agora e redundante

# Banco de origem (IBGE)

PostgreSQL com 11 tabelas montadas a partir de APIs públicas do IBGE.

| Fonte (API do IBGE) | Tabelas |
|---|---|
| Localidades | regiao, uf, mesorregiao, microrregiao, municipio, distrito |
| Agregados 7060 (IPCA) e 7063 (INPC) | area_ipca, categoria_produto, ipca_valor, inpc_valor |
| Agregados 6579 (população estimada) | populacao_municipio |

## Como subir

```bash
cd origem
copy .env.example .env          # Windows (no Linux/Mac: cp)
docker compose up -d

python -m venv .venv
.venv\Scripts\activate          # Windows (no Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

python scripts/carga_localidades.py
python scripts/carga_indice_precos.py ipca --reservar 1
python scripts/carga_indice_precos.py inpc --reservar 1
python scripts/carga_populacao.py
```

## Demonstração de carga incremental

```bash
python scripts/carga_indice_precos.py ipca --proximo   # traz o mês reservado
python scripts/carga_indice_precos.py inpc --proximo
```

## Demonstração de SCD tipo 2

```bash
python scripts/demo_alterar_dimensao.py             # altera nomes em duas dimensões
python scripts/demo_alterar_dimensao.py --reverter  # volta ao original
```

## Recriar o banco do zero

```bash
docker compose down -v
docker compose up -d
```

O arquivo `consultas/validacao.sql` traz as consultas de validação (contagens, datas, normalização).
O arquivo `modelo_origem.dbml` gera o diagrama em https://dbdiagram.io.
