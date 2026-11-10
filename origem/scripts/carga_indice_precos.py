"""Carrega IPCA (tabela 7060) ou INPC (tabela 7063) do IBGE para o PostgreSQL.

Uso (dentro da pasta origem):
    # Carga inicial: últimos 36 meses, deixando o ÚLTIMO mês de fora (para a demo incremental)
    python scripts/carga_indice_precos.py ipca --reservar 1

    # Carga incremental: traz apenas o próximo mês que ainda não está no banco
    python scripts/carga_indice_precos.py ipca --proximo

    # Carga completa, sem reservar nada
    python scripts/carga_indice_precos.py ipca

Troque "ipca" por "inpc" para o outro índice.
Pode rodar várias vezes: meses já carregados são pulados.
"""
import argparse
import re
import time
from datetime import date

from psycopg2.extras import execute_values

from comum import conectar, converter, get

API = "https://servicodados.ibge.gov.br/api/v3/agregados"
LOCALIDADES = "N1[all]|N6[all]|N7[all]"  # Brasil | municípios pesquisados | regiões metropolitanas

INDICES = {
    "ipca": {"agregado": 7060, "tabela": "ipca_valor"},
    "inpc": {"agregado": 7063, "tabela": "inpc_valor"},
}

# coluna do banco -> trecho do nome da variável no IBGE (minúsculo)
MEDIDAS = {
    "variacao_mensal": "variação mensal",
    "acumulado_ano": "acumulada no ano",
    "acumulado_12m": "12 meses",
    "peso_mensal": "peso mensal",
}


def metadados(agregado):
    """Descobre os códigos das variáveis e da classificação direto na API."""
    meta = get(f"{API}/{agregado}/metadados")
    variaveis = {}
    for v in meta["variaveis"]:
        nome = v["nome"].lower()
        for coluna, trecho in MEDIDAS.items():
            if trecho in nome:
                variaveis[str(v["id"])] = coluna
    if set(variaveis.values()) != set(MEDIDAS):
        nomes = [v["nome"] for v in meta["variaveis"]]
        raise RuntimeError(f"Não achei todas as variáveis esperadas. A API tem: {nomes}")
    classificacao = str(meta["classificacoes"][0]["id"])
    return variaveis, classificacao


def periodos_disponiveis(agregado):
    return sorted(p["id"] for p in get(f"{API}/{agregado}/periodos"))


def buscar_mes(agregado, periodo, variaveis, classificacao):
    url = f"{API}/{agregado}/periodos/{periodo}/variaveis/{'|'.join(variaveis)}"
    params = {"localidades": LOCALIDADES, "classificacao": f"{classificacao}[all]"}
    return get(url, params)


def nivel_categoria(nome):
    """Deduz o nível pelo código no início do nome: '1.' grupo, '11.' subgrupo, '1101.' item, '1101002.' subitem."""
    m = re.match(r"^(\d+)\.", nome)
    if not m:
        return "geral" if "geral" in nome.lower() else "indefinido"
    return {1: "grupo", 2: "subgrupo", 4: "item", 7: "subitem"}.get(len(m.group(1)), "indefinido")


def transformar(resposta, variaveis, periodo):
    """Converte o JSON da API em dicionários prontos para gravar."""
    areas, categorias, fatos = {}, {}, {}
    for var in resposta:
        coluna = variaveis[str(var["id"])]
        for res in var["resultados"]:
            (cat_id, cat_nome), = res["classificacoes"][0]["categoria"].items()
            categorias[int(cat_id)] = cat_nome
            for serie in res["series"]:
                loc = serie["localidade"]
                area_id = int(loc["id"])
                areas[area_id] = (loc["nome"], loc["nivel"]["nome"])
                valor = converter(serie["serie"].get(periodo))
                fatos.setdefault((area_id, int(cat_id)), {})[coluna] = valor
    return areas, categorias, fatos


def gravar(conn, tabela, periodo, areas, categorias, fatos):
    data = date(int(periodo[:4]), int(periodo[4:6]), 1)
    linhas = [
        (a, c, data, m.get("variacao_mensal"), m.get("acumulado_ano"),
         m.get("acumulado_12m"), m.get("peso_mensal"))
        for (a, c), m in fatos.items()
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO area_ipca (id, nome, nivel) VALUES %s ON CONFLICT (id) DO NOTHING",
            [(i, nome, nivel) for i, (nome, nivel) in areas.items()],
        )
        execute_values(
            cur,
            "INSERT INTO categoria_produto (id, nome, nivel) VALUES %s ON CONFLICT (id) DO NOTHING",
            [(i, nome, nivel_categoria(nome)) for i, nome in categorias.items()],
        )
        execute_values(
            cur,
            f"""
            INSERT INTO {tabela}
                (area_id, categoria_id, periodo, variacao_mensal, acumulado_ano, acumulado_12m, peso_mensal)
            VALUES %s
            ON CONFLICT (area_id, categoria_id, periodo) DO UPDATE SET
                variacao_mensal = EXCLUDED.variacao_mensal,
                acumulado_ano   = EXCLUDED.acumulado_ano,
                acumulado_12m   = EXCLUDED.acumulado_12m,
                peso_mensal     = EXCLUDED.peso_mensal
            WHERE ({tabela}.variacao_mensal, {tabela}.acumulado_ano, {tabela}.acumulado_12m, {tabela}.peso_mensal)
                  IS DISTINCT FROM
                  (EXCLUDED.variacao_mensal, EXCLUDED.acumulado_ano, EXCLUDED.acumulado_12m, EXCLUDED.peso_mensal)
            """,
            linhas,
            page_size=5000,
        )
    conn.commit()
    return len(linhas)


def main():
    parser = argparse.ArgumentParser(description="Carga de IPCA/INPC do IBGE")
    parser.add_argument("indice", choices=INDICES)
    parser.add_argument("--meses", type=int, default=36, help="tamanho da janela (padrão: 36 meses)")
    parser.add_argument("--reservar", type=int, default=0,
                        help="quantos meses finais NÃO carregar (guardados para a demo incremental)")
    parser.add_argument("--proximo", action="store_true",
                        help="carrega só o próximo mês ainda ausente no banco")
    args = parser.parse_args()

    cfg = INDICES[args.indice]
    variaveis, classificacao = metadados(cfg["agregado"])
    print("Variáveis encontradas:", variaveis)

    periodos = periodos_disponiveis(cfg["agregado"])
    janela = periodos[-args.meses:]
    print(f"Janela: {janela[0]} até {janela[-1]} ({len(janela)} meses)")

    conn = conectar()
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT to_char(periodo, 'YYYYMM') FROM {cfg['tabela']}")
        carregados = {linha[0] for linha in cur.fetchall()}

    if args.proximo:
        pendentes = [p for p in janela if p not in carregados][:1]
    else:
        alvo = janela[:-args.reservar] if args.reservar else janela
        pendentes = [p for p in alvo if p not in carregados]

    if not pendentes:
        print("Nada a carregar: todos os meses pedidos já estão no banco.")
        return

    for periodo in pendentes:
        print(f"Baixando {args.indice.upper()} {periodo}...")
        resposta = buscar_mes(cfg["agregado"], periodo, variaveis, classificacao)
        areas, categorias, fatos = transformar(resposta, variaveis, periodo)
        qtd = gravar(conn, cfg["tabela"], periodo, areas, categorias, fatos)
        print(f"  {periodo}: {qtd} linhas gravadas")
        time.sleep(1)

    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*), min(periodo), max(periodo) FROM {cfg['tabela']}")
        total, menor, maior = cur.fetchone()
    print(f"{cfg['tabela']}: {total} linhas, de {menor} a {maior}")
    conn.close()


if __name__ == "__main__":
    main()
