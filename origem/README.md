# Banco de origem (IBGE, dados reais)

PostgreSQL com **12 tabelas** montadas a partir de dados públicos do IBGE. Nenhum dado é inventado:
as tabelas grandes são **amostras reprodutíveis de dados reais**.

| Tabela | Fonte | Conteúdo |
|---|---|---|
| `municipio` | API de Localidades | 5.570 municípios, com microrregião, mesorregião, UF e região em colunas |
| `categoria_produto` | SIDRA 7060/7063 | produtos e serviços do IPCA/INPC (geral, grupo, subgrupo, item, subitem) |
| `ipca_valor`, `inpc_valor` | SIDRA 7060 e 7063 | inflação mensal, acumulada no ano, em 12 meses e peso (Brasil, 36 meses) |
| `populacao_municipio` | SIDRA 6579 | população estimada por município (3 anos) |
| `pib_municipio` | SIDRA 5938 | PIB e valor adicionado por setor, por município e ano |
| `producao_agricola` | SIDRA 5457 | lavouras por município e cultura |
| `rebanho_municipio` | SIDRA 3939 | efetivo dos rebanhos por município e tipo |
| `producao_origem_animal` | SIDRA 74 | leite, ovos etc., por município |
| `pnad_domicilio` → `pnad_morador` → `pnad_ocupacao` | PNAD Contínua (microdados) | respostas dos questionários: casa, pessoas e trabalho |

## Subir o banco (jeito rápido)

Pré-requisito: Docker Desktop aberto.

```bash
cd origem
copy .env.example .env     # Windows (Linux/Mac: cp .env.example .env)
docker compose up -d
```

Na **primeira vez** o Docker restaura sozinho o arquivo `sql/02_banco_completo.sql.gz` (leva alguns segundos).
Não é preciso rodar nenhuma carga nem baixar a PNAD.

Dados de conexão: host `localhost`, porta `5432`, banco `ibge_origem`, usuário e senha do arquivo `.env`.

> A restauração só acontece quando o banco está vazio. Para recomeçar do zero (**apaga todos os dados**):
> `docker compose down -v` e depois `docker compose up -d`.

## Como o banco foi montado (para refazer do zero)

O arquivo `sql/02_banco_completo.sql.gz` é uma cópia (dump) do banco já carregado pelos scripts abaixo.

```bash
python -m venv .venv
.venv\Scripts\activate     # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python scripts/carregar_tudo.py
python scripts/carga_pnad.py
```

A PNAD usa arquivos grandes (~200 MB cada) que **não ficam no GitHub**:

1. Em https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/
   baixe um arquivo de cada ano (`PNADC_022024.zip`, `PNADC_022025.zip`, `PNADC_022026.zip`) e coloque em `origem/dados/`.
2. Na pasta `Documentacao`, baixe `Dicionario_e_input_....zip` e coloque também em `origem/dados/`.

Para refazer do zero em um banco **vazio** sem usar o dump, mova o `sql/02_banco_completo.sql.gz` para outra pasta
e use o schema inicial em `schema/schema_inicial.sql` (ele cria 8 tabelas; as outras 4 são criadas pelos scripts de carga).

## Demonstração de carga incremental

O IPCA e o INPC ficam **sem o último mês** de propósito.

```bash
python scripts/carga_indice_precos.py ipca --proximo   # traz o mês reservado
python scripts/carga_indice_precos.py inpc --proximo
```

## Demonstração de SCD tipo 2

```bash
python scripts/demo_alterar_dimensao.py             # altera nomes em duas dimensões
python scripts/demo_alterar_dimensao.py --reverter  # volta ao original
```

## Atualizar o dump (só se o banco mudar)

Dentro da pasta `origem`, com o banco no ar:

```bash
docker exec ibge_postgres sh -c "pg_dump -U admin -d ibge_origem --no-owner --no-privileges | gzip > /tmp/banco.sql.gz"
docker cp ibge_postgres:/tmp/banco.sql.gz sql/02_banco_completo.sql.gz
```

## Validação e diagrama

- `consultas/validacao.sql`: contagens, datas e integridade.
- `python scripts/gerar_dbml.py`: gera `modelo_origem.dbml` a partir do banco real (https://dbdiagram.io/d).
