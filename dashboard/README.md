# Dashboard

One Page View com 4 KPIs e 2 métricas, construído em **Streamlit**. O
dashboard lê as tabelas da **camada gold** (Delta Lake) direto do **MinIO**,
sem precisar de Spark para visualizar.

## Indicadores

**KPIs**

1. **PIB per capita** — PIB total ÷ população (`economia_municipal`)
2. **Crescimento do PIB (%)** — variação em relação ao ano anterior (`economia_municipal`)
3. **IPCA acumulado em 12 meses** — índice geral, Brasil (`inflacao`)
4. **Taxa de desocupação (%)** — PNAD Contínua, último trimestre (`mercado_trabalho`)

**Métricas**

1. **População total** (`economia_municipal`)
2. **Valor da produção agrícola (R$)** (`agropecuaria_municipal`)

Filtros: ano, região e UF.

## Como executar

Pré-requisito: o pipeline já precisa ter sido executado (buckets → landing →
bronze → silver → gold), com o MinIO no ar via `docker compose up -d` na raiz
do projeto.

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

O dashboard abre em `http://localhost:8501`.

Caso o MinIO esteja em outro endereço ou com outras credenciais, use as
variáveis de ambiente `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
e `GOLD_URI`.

## Fonte dos dados

IBGE (SIDRA e PNAD Contínua), passando por todo o pipeline medalhão:
PostgreSQL → landing (CSV) → bronze → silver → gold (Delta Lake no MinIO) →
Streamlit.
