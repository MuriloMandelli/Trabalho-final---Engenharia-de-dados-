"""Dashboard do trabalho final de Engenharia de Dados (IBGE).

Lê as tabelas da camada gold (Delta Lake) no MinIO e monta a visão de uma
página com 4 KPIs, 2 métricas e os gráficos.
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from deltalake import DeltaTable

GOLD = os.getenv("GOLD_URI", "s3://gold")
STORAGE_OPTIONS = {
    "AWS_ENDPOINT_URL": os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000"),
    "AWS_ACCESS_KEY_ID": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("MINIO_SECRET_KEY", "miniopass"),
    "AWS_REGION": "us-east-1",
    "AWS_ALLOW_HTTP": "true",
    "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
}

AZUL = "#1565c0"
AZUL_CLARO = "#64b5f6"
LARANJA = "#ef6c00"
VERDE = "#2e7d32"

UF_INFO = {
    11: ("RO", "Norte"), 12: ("AC", "Norte"), 13: ("AM", "Norte"),
    14: ("RR", "Norte"), 15: ("PA", "Norte"), 16: ("AP", "Norte"),
    17: ("TO", "Norte"), 21: ("MA", "Nordeste"), 22: ("PI", "Nordeste"),
    23: ("CE", "Nordeste"), 24: ("RN", "Nordeste"), 25: ("PB", "Nordeste"),
    26: ("PE", "Nordeste"), 27: ("AL", "Nordeste"), 28: ("SE", "Nordeste"),
    29: ("BA", "Nordeste"), 31: ("MG", "Sudeste"), 32: ("ES", "Sudeste"),
    33: ("RJ", "Sudeste"), 35: ("SP", "Sudeste"), 41: ("PR", "Sul"),
    42: ("SC", "Sul"), 43: ("RS", "Sul"), 50: ("MS", "Centro-Oeste"),
    51: ("MT", "Centro-Oeste"), 52: ("GO", "Centro-Oeste"),
    53: ("DF", "Centro-Oeste"),
}

st.set_page_config(page_title="Dashboard IBGE", layout="wide")


@st.cache_data(show_spinner="Lendo a camada gold...")
def ler_gold(tabela: str) -> pd.DataFrame:
    dt = DeltaTable(f"{GOLD}/{tabela}", storage_options=STORAGE_OPTIONS)
    return dt.to_pandas()


# PIB e valor da produção vêm do IBGE em mil reais.
MIL = 1000


def moeda(valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    if abs(valor) >= 1_000_000_000_000:
        return f"R$ {valor / 1_000_000_000_000:,.2f} tri".replace(",", ".")
    if abs(valor) >= 1_000_000_000:
        return f"R$ {valor / 1_000_000_000:,.1f} bi".replace(",", ".")
    if abs(valor) >= 1_000_000:
        return f"R$ {valor / 1_000_000:,.1f} mi".replace(",", ".")
    return f"R$ {valor:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------
try:
    economia = ler_gold("economia_municipal")
    agro = ler_gold("agropecuaria_municipal")
    inflacao = ler_gold("inflacao")
    trabalho = ler_gold("mercado_trabalho")
except Exception as erro:  # noqa: BLE001
    st.error(
        "Não consegui ler a camada gold no MinIO.\n\n"
        "Confirme que o docker está no ar (`docker compose up -d`) e que o "
        "pipeline já foi executado (buckets → landing → bronze → silver → "
        "gold).\n\n"
        f"Detalhe técnico: {erro}"
    )
    st.stop()

trabalho = trabalho.copy()
trabalho["UF_CODIGO"] = pd.to_numeric(trabalho["UF_CODIGO"], errors="coerce")
trabalho["UF_SIGLA"] = trabalho["UF_CODIGO"].map(lambda c: UF_INFO.get(c, ("?", "?"))[0])
trabalho["REGIAO"] = trabalho["UF_CODIGO"].map(lambda c: UF_INFO.get(c, ("?", "?"))[1])

ano_pib = int(economia["ANO"].max())          # PIB municipal mais recente (2023)
ano_agro = int(agro["ANO"].max())             # produção agrícola mais recente (2025)

# ---------------------------------------------------------------------------
# Cabeçalho + filtros (Região / UF)
# ---------------------------------------------------------------------------
st.title("Economia e sociedade nos municípios brasileiros")
st.caption(
    "Dados públicos do IBGE (SIDRA e PNAD Contínua) · camada gold "
    "(Delta Lake / MinIO) · pipeline medalhão com Apache Spark"
)

regioes = sorted(r for r in economia["REGIAO"].dropna().unique())
c1, c2 = st.columns(2)
regiao = c1.selectbox("Região", ["Todas"] + regioes)
ufs_base = economia if regiao == "Todas" else economia[economia["REGIAO"] == regiao]
ufs = sorted(u for u in ufs_base["UF_SIGLA"].dropna().unique())
uf = c2.selectbox("UF", ["Todas"] + ufs)


def filtra(df: pd.DataFrame) -> pd.DataFrame:
    saida = df
    if regiao != "Todas" and "REGIAO" in saida.columns:
        saida = saida[saida["REGIAO"] == regiao]
    if uf != "Todas" and "UF_SIGLA" in saida.columns:
        saida = saida[saida["UF_SIGLA"] == uf]
    return saida


eco = filtra(economia[economia["ANO"] == ano_pib])
eco_ant = filtra(economia[economia["ANO"] == ano_pib - 1])
agro_f = filtra(agro[agro["ANO"] == ano_agro])

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
# 1) Crescimento do PIB (ano mais recente vs. anterior)
pib_atual = eco["PIB_TOTAL"].sum()
pib_ant = eco_ant["PIB_TOTAL"].sum()
cresc_pib = ((pib_atual / pib_ant - 1) * 100) if pib_ant else None

# 2) IPCA acumulado 12 meses (índice geral, Brasil, último mês)
ipca = inflacao[inflacao["INDICE"] == "IPCA"].copy()
ipca["PERIODO"] = pd.to_datetime(ipca["PERIODO"], errors="coerce")
geral = ipca[ipca["CATEGORIA"].str.contains("geral", case=False, na=False)]
if geral.empty:
    geral = ipca[ipca["PESO_MENSAL"] >= 99]
ipca_12m = None
mes_ipca = ""
if not geral.empty:
    ultimo = geral.sort_values("PERIODO").iloc[-1]
    ipca_12m = ultimo["ACUMULADO_12M"]
    mes_ipca = pd.to_datetime(ultimo["PERIODO"]).strftime("%m/%Y")

# 3 e 4) Taxa de desocupação e rendimento médio (PNAD, último trimestre)
trab_f = trabalho.copy()
if uf != "Todas":
    trab_f = trab_f[trab_f["UF_SIGLA"] == uf]
elif regiao != "Todas":
    trab_f = trab_f[trab_f["REGIAO"] == regiao]
taxa_desocup = None
rend_medio = None
periodo_pnad = ""
if not trab_f.empty:
    ano_t = int(trab_f["ANO"].max())
    tri_t = int(trab_f[trab_f["ANO"] == ano_t]["TRIMESTRE"].max())
    ult = trab_f[(trab_f["ANO"] == ano_t) & (trab_f["TRIMESTRE"] == tri_t)]
    forca = ult["POPULACAO_FORCA_TRABALHO"].sum()
    desoc = ult["POPULACAO_DESOCUPADA"].sum()
    ocup = ult["POPULACAO_OCUPADA"].sum()
    taxa_desocup = (desoc / forca * 100) if forca else None
    rend_medio = (
        (ult["RENDIMENTO_HABITUAL_MEDIO"] * ult["POPULACAO_OCUPADA"]).sum() / ocup
        if ocup else None
    )
    periodo_pnad = f"{tri_t}º tri/{ano_t}"

st.subheader("Indicadores")
k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Crescimento do PIB",
    "—" if cresc_pib is None else f"{cresc_pib:+.1f}%",
    help=f"PIB total de {ano_pib - 1} para {ano_pib}",
)
k2.metric(
    "IPCA acumulado 12 meses",
    "—" if ipca_12m is None else f"{ipca_12m:.2f}%",
    help=f"Índice geral, Brasil — {mes_ipca}",
)
k3.metric(
    "Taxa de desocupação",
    "—" if taxa_desocup is None else f"{taxa_desocup:.1f}%",
    help=f"PNAD Contínua — {periodo_pnad}",
)
k4.metric(
    "Rendimento médio do trabalho",
    moeda(rend_medio),
    help=f"Rendimento habitual médio dos ocupados — {periodo_pnad}",
)

# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
valor_agricola = agro_f["VALOR_PRODUCAO_AGRICOLA"].sum()

st.subheader("Métricas")
m1, m2 = st.columns(2)
m1.metric(
    "PIB total", moeda(pib_atual * MIL), help=f"Soma do PIB municipal — {ano_pib}"
)
m2.metric(
    "Valor da produção agrícola",
    moeda(valor_agricola * MIL),
    help=f"Soma do valor da produção — {ano_agro}",
)

st.divider()

# ---------------------------------------------------------------------------
# Gráficos (One Page View)
# ---------------------------------------------------------------------------
g1, g2 = st.columns(2)

# (a) PIB total por UF (em bilhões de reais)
base_uf = economia[economia["ANO"] == ano_pib]
if regiao != "Todas":
    base_uf = base_uf[base_uf["REGIAO"] == regiao]
por_uf = (
    base_uf.groupby("UF_SIGLA").agg(PIB=("PIB_TOTAL", "sum")).reset_index()
    .sort_values("PIB", ascending=False)
)
por_uf["PIB_BI"] = por_uf["PIB"] * MIL / 1_000_000_000
fig_uf = px.bar(
    por_uf, x="UF_SIGLA", y="PIB_BI",
    title=f"PIB total por UF — {ano_pib}",
    labels={"UF_SIGLA": "UF", "PIB_BI": "PIB (R$ bilhões)"},
    color_discrete_sequence=[AZUL],
)
fig_uf.update_layout(margin=dict(t=50, b=10, l=10, r=10))
g1.plotly_chart(fig_uf, use_container_width=True)

# (b) IPCA acumulado 12 meses ao longo do tempo
if not geral.empty:
    serie = geral.sort_values("PERIODO")[["PERIODO", "ACUMULADO_12M"]]
    fig_ipca = px.line(
        serie, x="PERIODO", y="ACUMULADO_12M", markers=True,
        title="IPCA acumulado em 12 meses — Brasil",
        labels={"PERIODO": "Mês", "ACUMULADO_12M": "IPCA 12m (%)"},
        color_discrete_sequence=[LARANJA],
    )
    fig_ipca.update_layout(margin=dict(t=50, b=10, l=10, r=10))
    g2.plotly_chart(fig_ipca, use_container_width=True)

g3, g4 = st.columns(2)

# (c) Valor da produção agrícola por UF (top 10)
base_agro = agro[agro["ANO"] == ano_agro]
if regiao != "Todas":
    base_agro = base_agro[base_agro["REGIAO"] == regiao]
agro_uf = (
    base_agro.groupby("UF_SIGLA")
    .agg(VALOR=("VALOR_PRODUCAO_AGRICOLA", "sum"))
    .reset_index()
)
agro_uf["VALOR_BI"] = agro_uf["VALOR"] * MIL / 1_000_000_000
agro_uf = agro_uf.sort_values("VALOR_BI", ascending=False).head(10)
fig_agro = px.bar(
    agro_uf.sort_values("VALOR_BI"), x="VALOR_BI", y="UF_SIGLA", orientation="h",
    title=f"Produção agrícola por UF (top 10) — {ano_agro}",
    labels={"VALOR_BI": "Valor da produção (R$ bilhões)", "UF_SIGLA": "UF"},
    color_discrete_sequence=[VERDE],
)
fig_agro.update_layout(margin=dict(t=50, b=10, l=10, r=10))
g3.plotly_chart(fig_agro, use_container_width=True)

# (d) Taxa de desocupação por UF (último trimestre disponível)
ano_t_all = int(trabalho["ANO"].max())
tri_all = int(trabalho[trabalho["ANO"] == ano_t_all]["TRIMESTRE"].max())
ult_all = trabalho[(trabalho["ANO"] == ano_t_all) & (trabalho["TRIMESTRE"] == tri_all)]
if regiao != "Todas":
    ult_all = ult_all[ult_all["REGIAO"] == regiao]
desoc_uf = (
    ult_all.groupby("UF_SIGLA")
    .agg(FORCA=("POPULACAO_FORCA_TRABALHO", "sum"),
         DESOC=("POPULACAO_DESOCUPADA", "sum"))
    .reset_index()
)
desoc_uf = desoc_uf[desoc_uf["FORCA"] > 0]
desoc_uf["TAXA"] = desoc_uf["DESOC"] / desoc_uf["FORCA"] * 100
desoc_uf = desoc_uf.sort_values("TAXA", ascending=False)
fig_desoc = px.bar(
    desoc_uf, x="UF_SIGLA", y="TAXA",
    title=f"Taxa de desocupação por UF — {tri_all}º tri/{ano_t_all}",
    labels={"UF_SIGLA": "UF", "TAXA": "Desocupação (%)"},
    color_discrete_sequence=[AZUL_CLARO],
)
fig_desoc.update_layout(margin=dict(t=50, b=10, l=10, r=10))
g4.plotly_chart(fig_desoc, use_container_width=True)

st.caption(
    "Fonte: IBGE (SIDRA e PNAD Contínua). Pipeline: PostgreSQL → MinIO "
    "(landing/bronze/silver/gold em Delta Lake) → Apache Spark → Streamlit. "
    "Cada indicador é exibido no período mais recente disponível na sua pesquisa."
)
