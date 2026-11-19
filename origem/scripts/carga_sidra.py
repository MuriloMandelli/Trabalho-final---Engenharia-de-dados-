"""Carga genérica de pesquisas municipais do IBGE (API de Dados Agregados / SIDRA).

Cria a tabela sozinha a partir do dicionário do próprio IBGE (uma coluna por indicador) e carrega
os dados REAIS dos últimos anos publicados. Nas pesquisas grandes (agricultura, pecuária) sorteia
municípios até chegar perto da quantidade de linhas pedida (--alvo).

Uso (dentro da pasta origem):
    python scripts/carga_sidra.py pib
    python scripts/carga_sidra.py agricola
    python scripts/carga_sidra.py rebanho
    python scripts/carga_sidra.py origem_animal
    python scripts/carga_sidra.py agricola --alvo 12000 --periodos 3
"""
import argparse
import random

from psycopg2.extras import execute_values

from comum import conectar, converter, get, slug

API = "https://servicodados.ibge.gov.br/api/v3/agregados"

DATASETS = {
    # alvo=None -> todos os municípios; "lote" = municípios por requisição (a API limita 100 mil valores)
    "pib": {"agregado": 5938, "tabela": "pib_municipio", "alvo": None, "lote": 100, "categoria": None},
    "agricola": {"agregado": 5457, "tabela": "producao_agricola", "alvo": 10500, "lote": 20, "categoria": "cultura"},
    "rebanho": {"agregado": 3939, "tabela": "rebanho_municipio", "alvo": 10500, "lote": 100, "categoria": "tipo_rebanho"},
    "origem_animal": {"agregado": 74, "tabela": "producao_origem_animal", "alvo": 10500, "lote": 100, "categoria": "produto"},
}

RESERVADOS = {"municipio_id", "ano", "atualizado_em"}
LIMITE_FALHAS = 25


def ler_metadados(agregado):
    meta = get(f"{API}/{agregado}/metadados")
    variaveis = [(str(v["id"]), v["nome"], v.get("unidade") or "") for v in meta["variaveis"]]
    classificacoes = [str(c["id"]) for c in meta.get("classificacoes", [])]
    return meta.get("nome", ""), variaveis, classificacoes


def nomear_colunas(variaveis, extras=()):
    """Variável do IBGE -> nome de coluna único (slug do nome; se repetir, acrescenta o código)."""
    usados = set(RESERVADOS) | set(extras)
    mapa = {}
    for vid, nome, _ in variaveis:
        col = slug(nome)
        if col in usados:
            col = f"{col[:44]}_{vid}"
        usados.add(col)
        mapa[vid] = col
    return mapa


def prefixos_categoria(cfg, quantidade):
    if quantidade == 0:
        return []
    base = cfg["categoria"] or "categoria"
    return [base] if quantidade == 1 else [f"{base}{i + 1}" for i in range(quantidade)]


def criar_tabela(conn, cfg, nome_pesquisa, variaveis, mapa, pref):
    tabela = cfg["tabela"]
    colunas = ["municipio_id INTEGER NOT NULL REFERENCES municipio(id)", "ano INTEGER NOT NULL"]
    pk = ["municipio_id", "ano"]
    for p in pref:
        colunas += [f"{p}_id INTEGER NOT NULL", f"{p}_nome VARCHAR(250)"]
        pk.append(f"{p}_id")
    colunas += [f"{mapa[vid]} NUMERIC" for vid, _, _ in variaveis]
    colunas.append("atualizado_em TIMESTAMP NOT NULL DEFAULT now()")
    with conn.cursor() as cur:
        cur.execute(f"CREATE TABLE IF NOT EXISTS {tabela} ({', '.join(colunas)}, PRIMARY KEY ({', '.join(pk)}))")
        cur.execute(f"CREATE OR REPLACE TRIGGER trg_{tabela}_atualizado BEFORE UPDATE ON {tabela} "
                    "FOR EACH ROW EXECUTE FUNCTION set_atualizado_em()")
        titulo = f"Fonte: IBGE/SIDRA tabela {cfg['agregado']} - {nome_pesquisa}".replace("'", "''")
        cur.execute(f"COMMENT ON TABLE {tabela} IS '{titulo}'")
        for vid, nome, unidade in variaveis:
            texto = f"{nome} ({unidade})".replace("'", "''")
            cur.execute(f"COMMENT ON COLUMN {tabela}.{mapa[vid]} IS '{texto}'")
    conn.commit()


def buscar(agregado, periodos, var_ids, class_ids, ids):
    url = f"{API}/{agregado}/periodos/{'|'.join(periodos)}/variaveis/{'|'.join(var_ids)}"
    params = {"localidades": "N6[" + ",".join(str(i) for i in ids) + "]"}
    if class_ids:
        params["classificacao"] = "|".join(f"{c}[all]" for c in class_ids)
    return get(url, params, tentativas=1)


def buscar_dividindo(ids, estado, **kw):
    """Se a API recusar o lote (ex.: passou de 100 mil valores), divide ao meio e tenta de novo."""
    try:
        return buscar(ids=ids, **kw)
    except Exception as erro:
        estado["falhas"] += 1
        if estado["falhas"] > LIMITE_FALHAS:
            raise RuntimeError(f"Muitas falhas seguidas na API. Último erro: {erro}")
        if len(ids) == 1:
            print(f"  município {ids[0]} ignorado: {erro}")
            return []
        meio = len(ids) // 2
        return buscar_dividindo(ids[:meio], estado, **kw) + buscar_dividindo(ids[meio:], estado, **kw)


def transformar(resposta, mapa):
    """JSON da API -> {(município, ano, categorias): {coluna: valor}} (descarta linhas sem nenhum número)."""
    linhas = {}
    for var in resposta:
        coluna = mapa[str(var["id"])]
        for res in var.get("resultados", []):
            cls, ignorar = [], False
            for c in res.get("classificacoes", []):
                (cid, cnome), = c["categoria"].items()
                if cnome.strip().lower() == "total":
                    ignorar = True  # evita somar o total junto com as partes
                cls.append((int(cid), cnome))
            if ignorar:
                continue
            for serie in res.get("series", []):
                mid = int(serie["localidade"]["id"])
                for periodo, texto in serie["serie"].items():
                    chave = (mid, int(periodo), tuple(cls))
                    linhas.setdefault(chave, {})[coluna] = converter(texto)
    return {k: d for k, d in linhas.items() if any(v is not None for v in d.values())}


def gravar(conn, tabela, pref, colunas_var, dados, municipios_validos):
    linhas = []
    for (mid, ano, cls), valores in dados.items():
        if mid not in municipios_validos or len(cls) != len(pref):
            continue
        linha = [mid, ano]
        for cid, cnome in cls:
            linha += [cid, cnome]
        linha += [valores.get(c) for c in colunas_var]
        linhas.append(tuple(linha))
    if not linhas:
        return 0
    cols = ["municipio_id", "ano"] + [f"{p}_{s}" for p in pref for s in ("id", "nome")] + colunas_var
    pk = ["municipio_id", "ano"] + [f"{p}_id" for p in pref]
    atualiza = ", ".join(f"{c} = EXCLUDED.{c}" for c in colunas_var)
    antigos = ", ".join(f"{tabela}.{c}" for c in colunas_var)
    novos = ", ".join(f"EXCLUDED.{c}" for c in colunas_var)
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES %s "
            f"ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {atualiza} "
            f"WHERE ({antigos}) IS DISTINCT FROM ({novos})",
            linhas,
            page_size=3000,
        )
    conn.commit()
    return len(linhas)


def lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


def main():
    parser = argparse.ArgumentParser(description="Carga de pesquisas municipais do IBGE")
    parser.add_argument("dataset", choices=DATASETS)
    parser.add_argument("--periodos", type=int, default=3, help="quantos anos (os mais recentes publicados)")
    parser.add_argument("--alvo", type=int, help="linhas desejadas (sorteia municípios até chegar perto)")
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    cfg = DATASETS[args.dataset]
    alvo = args.alvo if args.alvo is not None else cfg["alvo"]
    nome_pesquisa, variaveis, class_ids = ler_metadados(cfg["agregado"])
    pref = prefixos_categoria(cfg, len(class_ids))
    extras = [f"{p}_{s}" for p in pref for s in ("id", "nome")]
    mapa = nomear_colunas(variaveis, extras)
    colunas_var = [mapa[vid] for vid, _, _ in variaveis]
    var_ids = [vid for vid, _, _ in variaveis]
    print(f"Tabela {cfg['agregado']}: {nome_pesquisa}")
    print(f"  {len(variaveis)} indicadores, {len(class_ids)} classificação(ões)")

    periodos = sorted(p["id"] for p in get(f"{API}/{cfg['agregado']}/periodos"))[-args.periodos:]
    print(f"  anos: {periodos}")

    conn = conectar()
    criar_tabela(conn, cfg, nome_pesquisa, variaveis, mapa, pref)

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM municipio ORDER BY id")
        ids = [r[0] for r in cur.fetchall()]
    if not ids:
        raise SystemExit("A tabela municipio está vazia. Rode antes: python scripts/carga_localidades.py")
    validos = set(ids)
    random.Random(args.semente).shuffle(ids)

    estado = {"falhas": 0}
    gravadas = 0
    for n, lote in enumerate(lotes(ids, cfg["lote"]), start=1):
        resposta = buscar_dividindo(lote, estado, agregado=cfg["agregado"], periodos=periodos,
                                    var_ids=var_ids, class_ids=class_ids)
        dados = transformar(resposta, mapa)
        gravadas += gravar(conn, cfg["tabela"], pref, colunas_var, dados, validos)
        print(f"  lote {n}: {len(lote)} municípios -> {gravadas} linhas no total")
        if alvo and gravadas >= alvo:
            break

    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*), min(ano), max(ano), count(DISTINCT municipio_id) FROM {cfg['tabela']}")
        total, menor, maior, municipios = cur.fetchone()
    print(f"{cfg['tabela']}: {total} linhas, anos {menor}-{maior}, {municipios} municípios")
    conn.close()


if __name__ == "__main__":
    main()
