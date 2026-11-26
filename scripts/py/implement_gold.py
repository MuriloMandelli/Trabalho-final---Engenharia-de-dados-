import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://lakehouse_minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ibge_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ibge_origem")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")

from pyspark.sql import SparkSession, functions as Fun

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

caminho_silver = 's3a://silver'

df_categoria_produto = spark.read.format("delta").load(f"{caminho_silver}/categoria_produto")
df_inpc_valor = spark.read.format("delta").load(f"{caminho_silver}/inpc_valor")
df_ipca_valor = spark.read.format("delta").load(f"{caminho_silver}/ipca_valor")
df_municipio = spark.read.format("delta").load(f"{caminho_silver}/municipio")
df_pib_municipio = spark.read.format("delta").load(f"{caminho_silver}/pib_municipio")
df_pnad_domicilio = spark.read.format("delta").load(f"{caminho_silver}/pnad_domicilio")
df_pnad_morador = spark.read.format("delta").load(f"{caminho_silver}/pnad_morador")
df_pnad_ocupacao = spark.read.format("delta").load(f"{caminho_silver}/pnad_ocupacao")
df_populacao_municipio = spark.read.format("delta").load(f"{caminho_silver}/populacao_municipio")
df_producao_agricola = spark.read.format("delta").load(f"{caminho_silver}/producao_agricola")
df_producao_origem_animal = spark.read.format("delta").load(f"{caminho_silver}/producao_origem_animal")
df_rebanho_municipio = spark.read.format("delta").load(f"{caminho_silver}/rebanho_municipio")

def safe_drop(df, cols):
    existing = set(df.columns)
    to_drop = [c for c in cols if c in existing]
    return df.drop(*to_drop) if to_drop else df

dataframes = [
    df_categoria_produto, df_inpc_valor, df_ipca_valor, df_municipio, df_pib_municipio,df_pnad_domicilio,
    df_pnad_morador, df_pnad_ocupacao, df_populacao_municipio, df_producao_agricola, df_producao_origem_animal,
    df_rebanho_municipio
]

for currDf in dataframes:
    currDf = safe_drop(currDf, ["DATA_HORA_SILVER", "NOME_TABELA"])

dim_municipio = df_municipio.select(
    Fun.col("IDENTIFIER").alias("MUNICIPIO_ID"),
    Fun.col("NOME").alias("MUNICIPIO"),
    Fun.col("UNIDADE_DA_FEDERACAO_SIGLA").alias("UF_SIGLA"),
    Fun.col("UNIDADE_DA_FEDERACAO_NOME").alias("UF_NOME"),
    Fun.col("REGIAO_NOME").alias("REGIAO"),
)

fato_pib = df_pib_municipio.select(
    Fun.col("MUNICIPIO_IDENTIFIER").alias("MUNICIPIO_ID"),
    Fun.col("ANO").cast("int").alias("ANO"),
    Fun.col("PRODUTO_INTERNO_BRUTO_A_PRECOS_CORRENTES")
        .cast("double").alias("PIB_TOTAL"),
    Fun.col("VALOR_ADICIONADO_BRUTO_A_PRECOS_CORRENTES_TOTAL")
        .cast("double").alias("VALOR_ADICIONADO_TOTAL"),
    Fun.col("VALOR_ADICIONADO_BRUTO_A_PRECOS_CORRENTES_DA_AGROP")
        .cast("double").alias("VALOR_ADICIONADO_AGROPECUARIA"),
    Fun.col("VALOR_ADICIONADO_BRUTO_A_PRECOS_CORRENTES_DA_INDUS")
        .cast("double").alias("VALOR_ADICIONADO_INDUSTRIA"),
    Fun.col("VALOR_ADICIONADO_BRUTO_A_PRECOS_CORRENTES_DOS_SERV")
        .cast("double").alias("VALOR_ADICIONADO_SERVICOS"),
    Fun.col("VALOR_ADICIONADO_BRUTO_A_PRECOS_CORRENTES_DA_ADMIN")
        .cast("double").alias("VALOR_ADICIONADO_ADMINISTRACAO_PUBLICA"),
)

fato_populacao = df_populacao_municipio.select(
    Fun.col("MUNICIPIO_IDENTIFIER").alias("MUNICIPIO_ID"),
    Fun.col("ANO").cast("int").alias("ANO"),
    Fun.col("POPULACAO").cast("long").alias("POPULACAO"),
)

gold_economia_municipal = (
    fato_pib
    .join(fato_populacao, ["MUNICIPIO_ID", "ANO"], "left")
    .join(dim_municipio, "MUNICIPIO_ID", "left")
    .withColumn(
        "PIB_PER_CAPITA",
        Fun.when(
            Fun.col("POPULACAO") > 0,
            Fun.col("PIB_TOTAL") / Fun.col("POPULACAO"),
        ),
    )
    .select(
        "MUNICIPIO_ID", "MUNICIPIO", "UF_SIGLA", "UF_NOME", "REGIAO", "ANO",
        "POPULACAO", "PIB_TOTAL", "PIB_PER_CAPITA",
        "VALOR_ADICIONADO_TOTAL", "VALOR_ADICIONADO_AGROPECUARIA",
        "VALOR_ADICIONADO_INDUSTRIA", "VALOR_ADICIONADO_SERVICOS",
        "VALOR_ADICIONADO_ADMINISTRACAO_PUBLICA",
    )
)

agricola = (
    df_producao_agricola
    .groupBy(
        Fun.col("MUNICIPIO_IDENTIFIER").alias("MUNICIPIO_ID"),
        Fun.col("ANO").cast("int").alias("ANO"),
    )
    .agg(
        Fun.sum(Fun.col("VALOR_DA_PRODUCAO").cast("double"))
            .alias("VALOR_PRODUCAO_AGRICOLA"),
        Fun.sum(Fun.col("QUANTIDENTIFIERADE_PRODUZIDENTIFIERA").cast("double"))
            .alias("QUANTIDADE_PRODUZIDA_AGRICOLA"),
        Fun.sum(Fun.col("AREA_COLHIDENTIFIERA").cast("double"))
            .alias("AREA_COLHIDA_TOTAL"),
        Fun.countDistinct("CULTURA_IDENTIFIER").alias("QUANTIDADE_CULTURAS"),
    )
)

origem_animal = (
    df_producao_origem_animal
    .groupBy(
        Fun.col("MUNICIPIO_IDENTIFIER").alias("MUNICIPIO_ID"),
        Fun.col("ANO").cast("int").alias("ANO"),
    )
    .agg(
        Fun.sum(Fun.col("VALOR_DA_PRODUCAO").cast("double"))
            .alias("VALOR_PRODUCAO_ORIGEM_ANIMAL"),
        Fun.sum(Fun.col("PRODUCAO_DE_ORIGEM_ANIMAL").cast("double"))
            .alias("QUANTIDADE_PRODUCAO_ORIGEM_ANIMAL"),
        Fun.countDistinct("PRODUTO_IDENTIFIER")
            .alias("QUANTIDADE_PRODUTOS_ANIMAIS"),
    )
)

rebanhos = (
    df_rebanho_municipio
    .groupBy(
        Fun.col("MUNICIPIO_IDENTIFIER").alias("MUNICIPIO_ID"),
        Fun.col("ANO").cast("int").alias("ANO"),
    )
    .agg(
        Fun.sum(Fun.col("EFETIVO_DOS_REBANHOS").cast("double"))
            .alias("EFETIVO_TOTAL_REBANHOS"),
        Fun.countDistinct("TIPO_REBANHO_IDENTIFIER")
            .alias("QUANTIDADE_TIPOS_REBANHO"),
    )
)

gold_agropecuaria_municipal = (
    agricola
    .join(origem_animal, ["MUNICIPIO_ID", "ANO"], "full")
    .join(rebanhos, ["MUNICIPIO_ID", "ANO"], "full")
    .join(dim_municipio, "MUNICIPIO_ID", "left")
    .select(
        "MUNICIPIO_ID", "MUNICIPIO", "UF_SIGLA", "UF_NOME", "REGIAO", "ANO",
        "VALOR_PRODUCAO_AGRICOLA", "QUANTIDADE_PRODUZIDA_AGRICOLA",
        "AREA_COLHIDA_TOTAL", "QUANTIDADE_CULTURAS",
        "VALOR_PRODUCAO_ORIGEM_ANIMAL", "QUANTIDADE_PRODUCAO_ORIGEM_ANIMAL",
        "QUANTIDADE_PRODUTOS_ANIMAIS", "EFETIVO_TOTAL_REBANHOS",
        "QUANTIDADE_TIPOS_REBANHO",
    )
)

dim_categoria = df_categoria_produto.select(
    Fun.col("IDENTIFIER").alias("CATEGORIA_ID"),
    Fun.col("NOME").alias("CATEGORIA"),
    Fun.col("NIVEL").alias("NIVEL_CATEGORIA"),
)


def preparar_indice(df, nome_indice):
    return df.select(
        Fun.lit(nome_indice).alias("INDICE"),
        Fun.col("LOCALIDENTIFIERADE_IDENTIFIER").alias("LOCALIDADE_ID"),
        Fun.col("LOCALIDENTIFIERADE_NOME").alias("LOCALIDADE"),
        Fun.col("CATEGORIA_IDENTIFIER").alias("CATEGORIA_ID"),
        Fun.col("PERIODO"),
        Fun.col("VARIACAO_MENSAL").cast("double").alias("VARIACAO_MENSAL"),
        Fun.col("ACUMULADO_ANO").cast("double").alias("ACUMULADO_ANO"),
        Fun.col("ACUMULADO_12M").cast("double").alias("ACUMULADO_12M"),
        Fun.col("PESO_MENSAL").cast("double").alias("PESO_MENSAL"),
    )


gold_inflacao = (
    preparar_indice(df_ipca_valor, "IPCA")
    .unionByName(preparar_indice(df_inpc_valor, "INPC"))
    .join(dim_categoria, "CATEGORIA_ID", "left")
    .select(
        "INDICE", "LOCALIDADE_ID", "LOCALIDADE", "CATEGORIA_ID",
        "CATEGORIA", "NIVEL_CATEGORIA", "PERIODO", "VARIACAO_MENSAL",
        "ACUMULADO_ANO", "ACUMULADO_12M", "PESO_MENSAL",
    )
)

domicilios = df_pnad_domicilio.select(
    Fun.col("DOMICILIO_IDENTIFIER"),
    Fun.col("ANO").cast("int").alias("ANO"),
    Fun.col("TRIMESTRE").cast("int").alias("TRIMESTRE"),
    Fun.col("UNIDADE_DA_FEDERACAO").cast("string").alias("UF_CODIGO"),
)

moradores = df_pnad_morador.select(
    "MORADOR_IDENTIFIER",
    "DOMICILIO_IDENTIFIER",
    Fun.col("FORCA_DE_TRABALHO_NA_SEMANA_PARA_APLICAVEIS")
        .cast("int").alias("COD_FORCA_TRABALHO"),
    Fun.col("OCUPACAO_NA_SEMANA_PARA_APLICAVEIS")
        .cast("int").alias("COD_OCUPACAO"),
    Fun.col("PESO_DO_DOMICILIO_E_DAS_PESSOAS_COM_CALIBRACAO")
        .cast("double").alias("PESO_AMOSTRAL"),
)

ocupacoes = df_pnad_ocupacao.select(
    "MORADOR_IDENTIFIER",
    Fun.col(
        "RENDIMENTO_MENSAL_HABITUAL_EM_TODOS_OS_TRABALHOS_PARA_APLICAVEIS"
    ).cast("double").alias("RENDIMENTO_HABITUAL"),
    Fun.col(
        "RENDIMENTO_MENSAL_EFETIVO_EM_TODOS_OS_TRABALHOS_PARA_APLICAVEIS"
    ).cast("double").alias("RENDIMENTO_EFETIVO"),
    Fun.col(
        "HORAS_TRABALHADAS_HABITUAL_EM_TODOS_OS_TRABALHOS_PARA_APLICAVEIS"
    ).cast("double").alias("HORAS_HABITUAIS"),
    Fun.col(
        "GRUPAMENTOS_DE_ATIVADADE_NO_TRABALHO_PRINCIPAL_PARA_APLICAVEIS"
    ).alias("GRUPAMENTO_ATIVIDADE"),
)

pnad = (
    moradores
    .join(domicilios, "DOMICILIO_IDENTIFIER", "inner")
    .join(ocupacoes, "MORADOR_IDENTIFIER", "left")
    .filter(Fun.col("PESO_AMOSTRAL").isNotNull() & (Fun.col("PESO_AMOSTRAL") > 0))
    .withColumn("NA_FORCA_TRABALHO", Fun.col("COD_FORCA_TRABALHO") == 1)
    .withColumn("OCUPADO", Fun.col("COD_OCUPACAO") == 1)
    .withColumn(
        "PESO_FORCA_TRABALHO",
        Fun.when(Fun.col("NA_FORCA_TRABALHO"), Fun.col("PESO_AMOSTRAL")).otherwise(0.0),
    )
    .withColumn(
        "PESO_OCUPADO",
        Fun.when(Fun.col("OCUPADO"), Fun.col("PESO_AMOSTRAL")).otherwise(0.0),
    )
)

gold_mercado_trabalho = (
    pnad
    .groupBy("UF_CODIGO", "ANO", "TRIMESTRE")
    .agg(
        Fun.sum("PESO_AMOSTRAL").alias("POPULACAO_ESTIMADA_AMOSTRA"),
        Fun.sum("PESO_FORCA_TRABALHO").alias("POPULACAO_FORCA_TRABALHO"),
        Fun.sum("PESO_OCUPADO").alias("POPULACAO_OCUPADA"),
        Fun.sum(
            Fun.when(
                Fun.col("NA_FORCA_TRABALHO") & (~Fun.col("OCUPADO")),
                Fun.col("PESO_AMOSTRAL"),
            ).otherwise(0.0)
        ).alias("POPULACAO_DESOCUPADA"),
        Fun.sum(
            Fun.when(
                Fun.col("OCUPADO") & Fun.col("RENDIMENTO_HABITUAL").isNotNull(),
                Fun.col("PESO_AMOSTRAL") * Fun.col("RENDIMENTO_HABITUAL"),
            ).otherwise(0.0)
        ).alias("_SOMA_RENDIMENTO_HABITUAL_PONDERADO"),
        Fun.sum(
            Fun.when(
                Fun.col("OCUPADO") & Fun.col("RENDIMENTO_HABITUAL").isNotNull(),
                Fun.col("PESO_AMOSTRAL"),
            ).otherwise(0.0)
        ).alias("_PESO_RENDIMENTO_HABITUAL"),
        Fun.sum(
            Fun.when(
                Fun.col("OCUPADO") & Fun.col("RENDIMENTO_EFETIVO").isNotNull(),
                Fun.col("PESO_AMOSTRAL") * Fun.col("RENDIMENTO_EFETIVO"),
            ).otherwise(0.0)
        ).alias("_SOMA_RENDIMENTO_EFETIVO_PONDERADO"),
        Fun.sum(
            Fun.when(
                Fun.col("OCUPADO") & Fun.col("RENDIMENTO_EFETIVO").isNotNull(),
                Fun.col("PESO_AMOSTRAL"),
            ).otherwise(0.0)
        ).alias("_PESO_RENDIMENTO_EFETIVO"),
        Fun.sum(
            Fun.when(
                Fun.col("OCUPADO") & Fun.col("HORAS_HABITUAIS").isNotNull(),
                Fun.col("PESO_AMOSTRAL") * Fun.col("HORAS_HABITUAIS"),
            ).otherwise(0.0)
        ).alias("_SOMA_HORAS_HABITUAIS_PONDERADA"),
        Fun.sum(
            Fun.when(
                Fun.col("OCUPADO") & Fun.col("HORAS_HABITUAIS").isNotNull(),
                Fun.col("PESO_AMOSTRAL"),
            ).otherwise(0.0)
        ).alias("_PESO_HORAS_HABITUAIS"),
    )
    .withColumn(
        "TAXA_DESOCUPACAO_PERCENTUAL",
        Fun.when(
            Fun.col("POPULACAO_FORCA_TRABALHO") > 0,
            Fun.col("POPULACAO_DESOCUPADA")
            / Fun.col("POPULACAO_FORCA_TRABALHO") * 100,
        ),
    )
    .withColumn(
        "TAXA_OCUPACAO_NA_FORCA_TRABALHO_PERCENTUAL",
        Fun.when(
            Fun.col("POPULACAO_FORCA_TRABALHO") > 0,
            Fun.col("POPULACAO_OCUPADA")
            / Fun.col("POPULACAO_FORCA_TRABALHO") * 100,
        ),
    )
    .withColumn(
        "RENDIMENTO_HABITUAL_MEDIO",
        Fun.when(
            Fun.col("_PESO_RENDIMENTO_HABITUAL") > 0,
            Fun.col("_SOMA_RENDIMENTO_HABITUAL_PONDERADO")
            / Fun.col("_PESO_RENDIMENTO_HABITUAL"),
        ),
    )
    .withColumn(
        "RENDIMENTO_EFETIVO_MEDIO",
        Fun.when(
            Fun.col("_PESO_RENDIMENTO_EFETIVO") > 0,
            Fun.col("_SOMA_RENDIMENTO_EFETIVO_PONDERADO")
            / Fun.col("_PESO_RENDIMENTO_EFETIVO"),
        ),
    )
    .withColumn(
        "HORAS_HABITUAIS_MEDIAS",
        Fun.when(
            Fun.col("_PESO_HORAS_HABITUAIS") > 0,
            Fun.col("_SOMA_HORAS_HABITUAIS_PONDERADA")
            / Fun.col("_PESO_HORAS_HABITUAIS"),
        ),
    )
    .drop(
        "_SOMA_RENDIMENTO_HABITUAL_PONDERADO",
        "_PESO_RENDIMENTO_HABITUAL",
        "_SOMA_RENDIMENTO_EFETIVO_PONDERADO",
        "_PESO_RENDIMENTO_EFETIVO",
        "_SOMA_HORAS_HABITUAIS_PONDERADA",
        "_PESO_HORAS_HABITUAIS",
    )
)

caminho_gold = 's3a://gold'


gold_economia_municipal.write.format("delta").mode("overwrite").save(f"{caminho_gold}/economia_municipal")
gold_agropecuaria_municipal.write.format("delta").mode("overwrite").save(f"{caminho_gold}/agropecuaria_municipal")
gold_inflacao.write.format("delta").mode("overwrite").save(f"{caminho_gold}/inflacao")
gold_mercado_trabalho.write.format("delta").mode("overwrite").save(f"{caminho_gold}/mercado_trabalho")
