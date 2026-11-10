"""Carrega a população estimada por município (SIDRA, tabela 6579).

Uso (dentro da pasta origem):  python scripts/carga_populacao.py [--anos 3]
Pega os ÚLTIMOS N anos disponíveis na tabela (anos de Censo podem não existir nela).
Precisa rodar DEPOIS de carga_localidades.py (depende da tabela municipio).
"""
import argparse

from psycopg2.extras import execute_values

from comum import conectar, converter, get

API = "https://servicodados.ibge.gov.br/api/v3/agregados"
AGREGADO = 6579


def main():
    parser = argparse.ArgumentParser(description="Carga de população estimada")
    parser.add_argument("--anos", type=int, default=3)
    args = parser.parse_args()

    meta = get(f"{API}/{AGREGADO}/metadados")
    variavel = next((v["id"] for v in meta["variaveis"] if "estimada" in v["nome"].lower()), None)
    if variavel is None:
        raise RuntimeError("Variável de população estimada não encontrada na tabela 6579.")

    periodos = sorted(p["id"] for p in get(f"{API}/{AGREGADO}/periodos"))
    escolhidos = periodos[-args.anos:]
    print("Anos que serão carregados:", escolhidos)

    url = f"{API}/{AGREGADO}/periodos/{'|'.join(escolhidos)}/variaveis/{variavel}"
    resposta = get(url, params={"localidades": "N6[all]"})

    conn = conectar()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM municipio")
        existentes = {linha[0] for linha in cur.fetchall()}

    linhas, ignorados = [], 0
    for var in resposta:
        for res in var["resultados"]:
            for serie in res["series"]:
                municipio_id = int(serie["localidade"]["id"])
                if municipio_id not in existentes:
                    ignorados += 1
                    continue
                for ano, valor in serie["serie"].items():
                    pop = converter(valor)
                    if pop is not None:
                        linhas.append((municipio_id, int(ano), int(pop)))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO populacao_municipio (municipio_id, ano, populacao) VALUES %s
            ON CONFLICT (municipio_id, ano) DO UPDATE SET populacao = EXCLUDED.populacao
            WHERE populacao_municipio.populacao IS DISTINCT FROM EXCLUDED.populacao
            """,
            linhas,
            page_size=5000,
        )
    conn.commit()
    conn.close()
    print(f"populacao_municipio: {len(linhas)} linhas gravadas ({ignorados} municípios ignorados por não existirem em 'municipio')")


if __name__ == "__main__":
    main()
