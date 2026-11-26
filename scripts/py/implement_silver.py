import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://lakehouse_minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ibge_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ibge_origem")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")

from pyspark.sql import SparkSession

builder = (
    SparkSession.builder
    .appName("MinIO-Delta-Lake")
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
    .config("spark.hadoop.fs.s3a.endpoint.region", "us-east-1")
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
)

spark = builder.getOrCreate()

caminho_bronze = 's3a://bronze'

df_categoria_produto = spark.read.format("delta").load(f"{caminho_bronze}/categoria_produto")
df_inpc_valor = spark.read.format("delta").load(f"{caminho_bronze}/inpc_valor")
df_ipca_valor = spark.read.format("delta").load(f"{caminho_bronze}/ipca_valor")
df_municipio = spark.read.format("delta").load(f"{caminho_bronze}/municipio")
df_pib_municipio = spark.read.format("delta").load(f"{caminho_bronze}/pib_municipio")
df_pnad_domicilio = spark.read.format("delta").load(f"{caminho_bronze}/pnad_domicilio")
df_pnad_morador = spark.read.format("delta").load(f"{caminho_bronze}/pnad_morador")
df_pnad_ocupacao = spark.read.format("delta").load(f"{caminho_bronze}/pnad_ocupacao")
df_populacao_municipio = spark.read.format("delta").load(f"{caminho_bronze}/populacao_municipio")
df_producao_agricola = spark.read.format("delta").load(f"{caminho_bronze}/producao_agricola")
df_producao_origem_animal = spark.read.format("delta").load(f"{caminho_bronze}/producao_origem_animal")
df_rebanho_municipio = spark.read.format("delta").load(f"{caminho_bronze}/rebanho_municipio")

from pyspark.sql.functions import current_timestamp, lit

df_categoria_produto = df_categoria_produto.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("categoria_produto"))
df_inpc_valor = df_inpc_valor.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("inpc_valor"))
df_ipca_valor = df_ipca_valor.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("ipca_valor"))
df_municipio = df_municipio.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("municipio"))
df_pib_municipio = df_pib_municipio.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("pib_municipio"))
df_pnad_domicilio = df_pnad_domicilio.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("pnad_domicilio"))
df_pnad_morador = df_pnad_morador.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("pnad_morador"))
df_pnad_ocupacao = df_pnad_ocupacao.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("pnad_ocupacao"))
df_populacao_municipio = df_populacao_municipio.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("populacao_municipio"))
df_producao_agricola = df_producao_agricola.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("producao_agricola"))
df_producao_origem_animal = df_producao_origem_animal.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("producao_origem_animal"))
df_rebanho_municipio = df_rebanho_municipio.withColumn("data_hora_silver", current_timestamp()).withColumn("nome_tabela", lit("rebanho_municipio"))

values_columns = [
    ["ID", "IDENTIFIER"],
    ["UF", "UNIDADE_DA_FEDERACAO"],
    ["CAPITAL", "MINICIPIO_DA_CAPITAL"],
    ["RM_RIDE", "REGIAO_METROPOLITANA_E_ADMINISTRATIVA_INTEGRADA_DE_DESENVOLVIMENTO"],
    ["UPA", "UNIDADE_PRIMARIA_DE_AMOSTRAGEM"],
    ["V1008", "NUMERO_DE_SELECAO_DO_DOMICILIO"],
    ["V1014", "PAINEL"],
    ["V1022", "SITUACAO_DO_DOMICILIO"],
    ["V1023", "TIPO_DE_AREA"],
    ["V2001", "NUMERO_DE_PESSOAS_NO_DOMICILIO"],
    ["V2003", "NUMERO_DE_ORDEM"],
    ["V2005", "CONDICAO_NO_DOMICILIO"],
    ["V2007", "SEXO"],
    ["V2009", "IDADE_DO_MORADOR_NA_DATA_DE_REFERENCIA"],
    ["V2010", "COR_OU_RACA"],
    ["V3001", "SABE_LER_E_ESCREVER"],
    ["V3002", "FREQUENTA_ESCOLA"],
    ["V3009A", "CURSO_MAIS_ELEVADO_FREQUENTADO"],
    ["VD3004", "NIVEL_DE_INSTRUCAO_MAIS_ELEVADO_ALCANCADO"],
    ["VD3005", "ANOS_DE_ESTUDO"],
    ["VD4001", "FORCA_DE_TRABALHO_NA_SEMANA_PARA_APLICAVEIS"],
    ["VD4002", "OCUPACAO_NA_SEMANA_PARA_APLICAVEIS"],
    ["V1027", "PESO_DO_DOMICILIO_E_DAS_PESSOAS_SEM_CALIBRACAO"],
    ["V1028", "PESO_DO_DOMICILIO_E_DAS_PESSOAS_COM_CALIBRACAO"],
    ["V1029", "PROJECAO_DA_POPULACAO_POR_NIVEIS_GEOGRAFICOS"],
    ["V4009", "QUANTOS_TRABALHOS_POR_SEMANA"],
    ["V4010", "CODIGO_DA_OCUPACAO"],
    ["V4012", "TIPO_DE_TRABALHO"],
    ["V4013", "CODIGO_ATIVIDADE_PRINCIPAL_DO_NEGOCIO_EMPRESA"],
    ["V4029", "TRABALHO_COM_CARTEIRA_DE_TRABALHO_ASSINADA"],
    ["V4032", "TRABALHO_ERA_CONTRIBUINTE_DE_INSTITUTO_DE_PREVEDENCIA"],
    ["V4039", "HORAS_TRABALHADAS_POR_SEMANA_NO_TRABALHO_PRINCIPAL"],
    ["VD4009", "POSICAO_NA_OCUPACAO_E_CATEGORIA_NO_TRABALHO_PRINCIPAL_PARA_APLICAVEIS"],
    ["VD4010", "GRUPAMENTOS_DE_ATIVADADE_NO_TRABALHO_PRINCIPAL_PARA_APLICAVEIS"],
    ["VD4011", "GRUPAMENTOS_OCUPACIONAIS_NO_TRABALHO_PRINCIPAL_PARA_APLICAVEIS"],
    ["VD4012", "CONTRIBUICAO_PARA_INSTITUTO_DE_PREVIDENCIA_PARA_APLICAVEIS"],
    ["VD4016", "RENDIMENTO_MENSAL_HABITUAL_NO_TRABALHO_PRINCIPAL_PARA_APLICAVEIS"],
    ["VD4017", "RENDIMENTO_MENSAL_EFETIVO_NO_TRABALHO_PRINCIPAL_PARA_APLICAVEIS"],
    ["VD4019", "RENDIMENTO_MENSAL_HABITUAL_EM_TODOS_OS_TRABALHOS_PARA_APLICAVEIS"],
    ["VD4020", "RENDIMENTO_MENSAL_EFETIVO_EM_TODOS_OS_TRABALHOS_PARA_APLICAVEIS"],
    ["VD4031", "HORAS_TRABALHADAS_HABITUAL_EM_TODOS_OS_TRABALHOS_PARA_APLICAVEIS"],
]


def apply_name_rules(colname: str) -> str:
    n = colname.upper()
    for columns in values_columns:
        n = n.replace(columns[0], columns[1])
    return n

def safe_drop(df, cols):
    existing = set(df.columns)
    to_drop = [c for c in cols if c in existing]
    return df.drop(*to_drop) if to_drop else df

dataframes = [
    df_categoria_produto, df_inpc_valor, df_ipca_valor, df_municipio, df_pib_municipio,df_pnad_domicilio,
    df_pnad_morador, df_pnad_ocupacao, df_populacao_municipio, df_producao_agricola, df_producao_origem_animal,
    df_rebanho_municipio
]
caminho_silver = 's3a://silver'

for currDf in dataframes:
    new_cols = [apply_name_rules(c) for c in currDf.columns]
    currDf = currDf.toDF(*new_cols)

    currDf = safe_drop(currDf, ["DATA_HORA_BRONZE", "NOME_ARQUIVO"])

    currDf.write.format("delta").mode("overwrite").save(f"{caminho_silver}/"+currDf.select("NOME_TABELA").first()["NOME_TABELA"])
