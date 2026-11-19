"""Mostra a "ficha" de uma ou mais tabelas da API de Dados Agregados do IBGE (SIDRA).

Serve para conferir ANTES de construir qualquer carga: nome, anos disponíveis,
níveis territoriais (N6 = município), variáveis e classificações (com a quantidade de categorias).

Uso (dentro da pasta origem, com o ambiente virtual ativo):
    python scripts/explorar_agregado.py 5938
    python scripts/explorar_agregado.py 5938 5457 3939 74 3940
"""
import sys

from comum import get

API = "https://servicodados.ibge.gov.br/api/v3/agregados"


def explorar(agregado):
    meta = get(f"{API}/{agregado}/metadados")
    print("=" * 72)
    print(f"TABELA {agregado}: {meta.get('nome')}")
    print("Pesquisa:", meta.get("pesquisa"))
    print("Assunto :", meta.get("assunto"))

    periodicidade = meta.get("periodicidade") or {}
    print("Periodicidade:", periodicidade.get("frequencia"),
          "| de", periodicidade.get("inicio"), "até", periodicidade.get("fim"))

    niveis = meta.get("nivelTerritorial") or {}
    print("Níveis territoriais (N6 = município):", niveis)

    print("Variáveis:")
    for v in meta.get("variaveis", []):
        print(f"   {v.get('id')}: {v.get('nome')} ({v.get('unidade')})")

    print("Classificações:")
    for c in meta.get("classificacoes", []):
        categorias = c.get("categorias", [])
        print(f"   {c.get('id')}: {c.get('nome')} -> {len(categorias)} categorias")
        for cat in categorias[:5]:
            print(f"        {cat.get('id')}: {cat.get('nome')}")
        if len(categorias) > 5:
            print("        ...")

    periodos = sorted(p["id"] for p in get(f"{API}/{agregado}/periodos"))
    print(f"Períodos: {len(periodos)} no total. Últimos: {periodos[-6:]}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/explorar_agregado.py NUMERO_DA_TABELA [OUTRA_TABELA ...]")
        return
    for agregado in sys.argv[1:]:
        try:
            explorar(agregado)
        except Exception as erro:  # mostra o erro e segue para a próxima tabela
            print(f"Tabela {agregado}: erro -> {erro}")


if __name__ == "__main__":
    main()
