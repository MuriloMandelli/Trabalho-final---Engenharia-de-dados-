"""Carrega regiões, UFs, mesorregiões, microrregiões, municípios e distritos.

Uso (dentro da pasta origem):  python scripts/carga_localidades.py
Pode rodar várias vezes: não duplica dados (ON CONFLICT DO NOTHING).
"""
from psycopg2.extras import execute_values

from comum import conectar, get

BASE = "https://servicodados.ibge.gov.br/api/v1/localidades"


def carregar(conn, tabela, colunas, linhas):
    sql = (
        f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES %s "
        "ON CONFLICT (id) DO NOTHING"
    )
    with conn.cursor() as cur:
        execute_values(cur, sql, linhas, page_size=2000)
    conn.commit()
    print(f"{tabela}: {len(linhas)} registros recebidos da API")


def main():
    conn = conectar()

    # A ordem importa: primeiro os "pais", depois os "filhos"
    carregar(conn, "regiao", ["id", "sigla", "nome"],
             [(r["id"], r["sigla"], r["nome"]) for r in get(f"{BASE}/regioes")])

    carregar(conn, "uf", ["id", "sigla", "nome", "regiao_id"],
             [(e["id"], e["sigla"], e["nome"], e["regiao"]["id"])
              for e in get(f"{BASE}/estados")])

    carregar(conn, "mesorregiao", ["id", "nome", "uf_id"],
             [(m["id"], m["nome"], m["UF"]["id"])
              for m in get(f"{BASE}/mesorregioes")])

    carregar(conn, "microrregiao", ["id", "nome", "mesorregiao_id"],
             [(m["id"], m["nome"], m["mesorregiao"]["id"])
              for m in get(f"{BASE}/microrregioes")])

    carregar(conn, "municipio", ["id", "nome", "microrregiao_id"],
             [(m["id"], m["nome"], (m.get("microrregiao") or {}).get("id"))
              for m in get(f"{BASE}/municipios")])

    carregar(conn, "distrito", ["id", "nome", "municipio_id"],
             [(d["id"], d["nome"], d["municipio"]["id"])
              for d in get(f"{BASE}/distritos")])

    conn.close()
    print("Carga de localidades concluída.")


if __name__ == "__main__":
    main()
