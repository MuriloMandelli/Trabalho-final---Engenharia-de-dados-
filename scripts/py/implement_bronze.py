import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ibge_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ibge_origem")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")

from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

packages = ["org.apache.hadoop:hadoop-aws:3.4.0"]

builder = (
    SparkSession.builder
    .appName("MinIO-Delta-Lake")
    .master("local[*]")
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

spark = configure_spark_with_delta_pip(
    builder,
    extra_packages=packages
).getOrCreate()

caminho_landing = 's3a://landing'

df_categoria_produto = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/categoria_produto.csv"))
df_inpc_valor = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/inpc_valor.csv"))
df_ipca_valor = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/ipca_valor.csv"))
df_municipio = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/municipio.csv"))
df_pib_municipio = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/pib_municipio.csv"))
df_pnad_domicilio = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/pnad_domicilio.csv"))
df_pnad_morador = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/pnad_morador.csv"))
df_pnad_ocupacao = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/pnad_ocupacao.csv"))
df_populacao_municipio = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/populacao_municipio.csv"))
df_producao_agricola = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/producao_agricola.csv"))
df_producao_origem_animal = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/producao_origem_animal.csv"))
df_rebanho_municipio = (spark.read.option("header", "true").option("inferSchema", "true").csv(f"{caminho_landing}/rebanho_municipio.csv"))

from pyspark.sql.functions import current_timestamp, lit

df_categoria_produto = df_categoria_produto.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("categoria_produto.csv"))
df_inpc_valor = df_inpc_valor.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("inpc_valor.csv"))
df_ipca_valor = df_ipca_valor.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("ipca_valor.csv"))
df_municipio = df_municipio.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("municipio.csv"))
df_pib_municipio = df_pib_municipio.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("pib_municipio.csv"))
df_pnad_domicilio = df_pnad_domicilio.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("pnad_domicilio.csv"))
df_pnad_morador = df_pnad_morador.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("pnad_morador.csv"))
df_pnad_ocupacao = df_pnad_ocupacao.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("pnad_ocupacao.csv"))
df_populacao_municipio = df_populacao_municipio.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("populacao_municipio.csv"))
df_producao_agricola = df_producao_agricola.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("producao_agricola.csv"))
df_producao_origem_animal = df_producao_origem_animal.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("producao_origem_animal.csv"))
df_rebanho_municipio = df_rebanho_municipio.withColumn("data_hora_bronze", current_timestamp()).withColumn("nome_arquivo", lit("rebanho_municipio.csv"))

caminho_bronze = 's3a://bronze'

df_categoria_produto.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/categoria_produto")
df_inpc_valor.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/inpc_valor")
df_ipca_valor.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/ipca_valor")
df_municipio.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/municipio")
df_pib_municipio.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/pib_municipio")
df_pnad_domicilio.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/pnad_domicilio")
df_pnad_morador.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/pnad_morador")
df_pnad_ocupacao.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/pnad_ocupacao")
df_populacao_municipio.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/populacao_municipio")
df_producao_agricola.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/producao_agricola")
df_producao_origem_animal.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/producao_origem_animal")
df_rebanho_municipio.write.format("delta").mode("overwrite").save(f"{caminho_bronze}/rebanho_municipio")
