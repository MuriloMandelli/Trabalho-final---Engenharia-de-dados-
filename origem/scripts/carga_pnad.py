"""Carrega uma AMOSTRA dos microdados da PNAD Contínua (respostas dos questionários do IBGE).

O arquivo original tem uma linha por pessoa, com os dados do domicílio repetidos em cada uma.
Aqui ele é NORMALIZADO em três tabelas: pnad_domicilio -> pnad_morador -> pnad_ocupacao.
Sorteia domicílios inteiros (todas as pessoas de cada um), sempre com a mesma semente.

Preparação (uma vez):
  1) Baixe 3 arquivos trimestrais (ex.: PNADC_022024.zip, PNADC_022025.zip, PNADC_022026.zip) de
     https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/
     (há uma pasta por ano) e coloque na pasta  origem/dados/
  2) Baixe o dicionário (pasta Documentacao, arquivo "Dicionario_e_input_....zip") e coloque também
     em origem/dados/ (pode ficar compactado).

Uso (dentro da pasta origem):
    python scripts/carga_pnad.py
    python scripts/carga_pnad.py --domicilios 3600 --uf 42     # só Santa Catarina
"""
import argparse
import io
import random
import re
import zipfile
from pathlib import Path

from psycopg2.extras import execute_values

import pnad_spec as spec
from comum import RAIZ, conectar

# Linha típica do arquivo de layout (SAS):  @0006 UF $2.     ou     @0063 V1028 15.8
PADRAO = re.compile(r"@\s*(\d+)\s+([A-Za-z0-9_]+)\s+(\$)?\s*(\d+)\.(\d*)")
CHAVE = ["ANO", "TRIMESTRE", "UPA", "V1008", "V1014"]


def ler_layout(caminho):
    """Lê o arquivo de layout do IBGE e devolve {VARIAVEL: (início, largura, é_texto, decimais)}."""
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".zip":
        with zipfile.ZipFile(caminho) as zf:
            candidatos = [n for n in zf.namelist()
                          if "input" in n.lower() and n.lower().endswith((".txt", ".sas"))]
            if not candidatos:
                raise RuntimeError(f"Nenhum arquivo 'input' dentro de {caminho.name}: {zf.namelist()}")
            texto = zf.read(candidatos[0]).decode("latin-1")
    else:
        texto = caminho.read_text(encoding="latin-1")
    layout = {}
    for pos, nome, char, largura, dec in PADRAO.findall(texto):
        layout[nome.upper()] = (int(pos) - 1, int(largura), bool(char), int(dec) if dec else 0)
    if not layout:
        raise RuntimeError("Não consegui ler o layout. Me mande as primeiras 30 linhas do arquivo 'input'.")
    return layout


def campo(linha, layout, nome):
    """Texto do campo (sem espaços) ou None se vazio/inexistente."""
    if nome.upper() not in layout:
        return None
    ini, larg, _, _ = layout[nome.upper()]
    texto = linha[ini:ini + larg].strip()
    return texto or None


def valor(linha, layout, nome, tipo):
    texto = campo(linha, layout, nome)
    if texto is None:
        return None
    if tipo == "txt":
        return texto
    try:
        numero = float(texto)
    except ValueError:
        return None
    decimais = layout[nome.upper()][3]
    if decimais and "." not in texto:
        numero /= 10 ** decimais
    return int(round(numero)) if tipo == "int" else numero


def abrir_linhas(caminho_zip):
    with zipfile.ZipFile(caminho_zip) as zf:
        membros = [n for n in zf.namelist() if not n.endswith("/")]
        txt = [n for n in membros if n.lower().endswith(".txt")]
        nome = txt[0] if txt else max(membros, key=lambda n: zf.getinfo(n).file_size)
        with zf.open(nome) as bruto:
            for linha in io.TextIOWrapper(bruto, encoding="latin-1", newline=None):
                yield linha.rstrip("\r\n")


def chave_domicilio(linha, layout):
    partes = tuple(campo(linha, layout, n) for n in CHAVE)
    return None if any(p is None for p in partes) else partes


def escolher_amostra(caminho_zip, layout, quantidade, uf, semente):
    """Passo 1: descobre todos os domicílios do arquivo e sorteia 'quantidade' deles."""
    chaves = set()
    for linha in abrir_linhas(caminho_zip):
        if uf and campo(linha, layout, "UF") != uf:
            continue
        k = chave_domicilio(linha, layout)
        if k:
            chaves.add(k)
    ordenadas = sorted(chaves)
    random.Random(semente).shuffle(ordenadas)
    return set(ordenadas[:quantidade]), len(chaves)


def montar_registros(caminho_zip, layout, amostra):
    """Passo 2: lê o arquivo de novo e monta as linhas das três tabelas."""
    domicilios, moradores, ocupacoes = {}, [], []
    for linha in abrir_linhas(caminho_zip):
        k = chave_domicilio(linha, layout)
        if k not in amostra:
            continue
        ano, tri, upa, v1008, v1014 = k
        dom_id = f"{ano}{tri}_{upa}_{v1008}_{v1014}"
        ordem = campo(linha, layout, "V2003")
        if ordem is None:
            continue
        if dom_id not in domicilios:
            domicilios[dom_id] = [dom_id] + [valor(linha, layout, v, t) for v, t, _ in spec.DOMICILIO]
        mor_id = f"{dom_id}_{ordem}"
        moradores.append([mor_id, dom_id] + [valor(linha, layout, v, t) for v, t, _ in spec.MORADOR])
        if campo(linha, layout, "VD4002") == "1":
            ocupacoes.append([mor_id] + [valor(linha, layout, v, t) for v, t, _ in spec.OCUPACAO])
    return list(domicilios.values()), moradores, ocupacoes


def gravar(conn, domicilios, moradores, ocupacoes):
    def inserir(cur, tabela, chave, colunas, linhas):
        if not linhas:
            return
        execute_values(
            cur,
            f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES %s ON CONFLICT ({chave}) DO NOTHING",
            [tuple(x) for x in linhas],
            page_size=5000,
        )

    with conn.cursor() as cur:
        inserir(cur, "pnad_domicilio", "domicilio_id",
                ["domicilio_id"] + [v.lower() for v, _, _ in spec.DOMICILIO], domicilios)
        inserir(cur, "pnad_morador", "morador_id",
                ["morador_id", "domicilio_id"] + [v.lower() for v, _, _ in spec.MORADOR], moradores)
        inserir(cur, "pnad_ocupacao", "morador_id",
                ["morador_id"] + [v.lower() for v, _, _ in spec.OCUPACAO], ocupacoes)
    conn.commit()


def achar_layout(pasta):
    candidatos = sorted(pasta.glob("*nput*"))
    if not candidatos:
        raise RuntimeError(
            f"Não achei o dicionário/layout em {pasta}. Coloque lá o arquivo 'Dicionario_e_input_....zip' "
            "(ou o arquivo 'input_PNADC_trimestral.txt'), ou use --layout.")
    return candidatos[0]


def main():
    parser = argparse.ArgumentParser(description="Carga (amostra) da PNAD Contínua")
    parser.add_argument("--pasta", default=str(RAIZ / "dados"), help="pasta com os PNADC_*.zip")
    parser.add_argument("--layout", help="arquivo de layout (padrão: procura em --pasta)")
    parser.add_argument("--domicilios", type=int, default=3600, help="domicílios sorteados por arquivo")
    parser.add_argument("--uf", help="filtra por código da UF (ex.: 42 = Santa Catarina)")
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    pasta = Path(args.pasta)
    arquivos = sorted(p for p in pasta.glob("PNADC_*.zip"))
    if not arquivos:
        raise SystemExit(f"Nenhum PNADC_*.zip em {pasta}. Veja as instruções no topo deste arquivo.")

    layout_path = Path(args.layout) if args.layout else achar_layout(pasta)
    layout = ler_layout(layout_path)
    print(f"Layout: {layout_path.name} ({len(layout)} variáveis)")

    todas = [v for v, _, _ in spec.DOMICILIO + spec.MORADOR + spec.OCUPACAO] + ["VD4002"]
    faltando = sorted({v for v in todas if v.upper() not in layout})
    if faltando:
        print("ATENÇÃO: variáveis que não existem no layout (colunas ficarão vazias):", faltando)

    conn = conectar()
    for arquivo in arquivos:
        print(f"\n{arquivo.name}: sorteando {args.domicilios} domicílios...")
        amostra, total = escolher_amostra(arquivo, layout, args.domicilios, args.uf, args.semente)
        print(f"  {len(amostra)} sorteados de {total} domicílios no arquivo")
        domicilios, moradores, ocupacoes = montar_registros(arquivo, layout, amostra)
        gravar(conn, domicilios, moradores, ocupacoes)
        print(f"  gravados: {len(domicilios)} domicílios, {len(moradores)} moradores, {len(ocupacoes)} ocupações")

    with conn.cursor() as cur:
        for tabela in ("pnad_domicilio", "pnad_morador", "pnad_ocupacao"):
            cur.execute(f"SELECT count(*) FROM {tabela}")
            print(f"{tabela}: {cur.fetchone()[0]} linhas")
    conn.close()


if __name__ == "__main__":
    main()
