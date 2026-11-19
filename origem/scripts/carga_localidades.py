
from psycopg2.extras import execute_values

from comum import conectar, get

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

COLUNAS = [
    "id", "nome",
    "microrregiao_id", "microrregiao_nome",
    "mesorregiao_id", "mesorregiao_nome",
    "uf_id", "uf_sigla", "uf_nome",
    "regiao_id", "regiao_sigla", "regiao_nome",
    "regiao_imediata_id", "regiao_imediata_nome",
    "regiao_intermediaria_id", "regiao_intermediaria_nome",
]


def achatar(m):
    """Transforma o JSON aninhado de um município em uma linha plana."""
    micro = m.get("microrregiao") or {}
    meso = micro.get("mesorregiao") or {}
    imediata = m.get("regiao-imediata") or {}
    intermediaria = imediata.get("regiao-intermediaria") or {}
    uf = meso.get("UF") or intermediaria.get("UF") or {}
    regiao = uf.get("regiao") or {}
    return (
        m["id"], m["nome"],
        micro.get("id"), micro.get("nome"),
        meso.get("id"), meso.get("nome"),
        uf.get("id"), uf.get("sigla"), uf.get("nome"),
        regiao.get("id"), regiao.get("sigla"), regiao.get("nome"),
        imediata.get("id"), imediata.get("nome"),
        intermediaria.get("id"), intermediaria.get("nome"),
    )


def main():
    linhas = [achatar(m) for m in get(URL)]
    conn = conectar()
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO municipio ({', '.join(COLUNAS)}) VALUES %s ON CONFLICT (id) DO NOTHING",
            linhas,
            page_size=2000,
        )
        cur.execute("SELECT count(*) FROM municipio")
        total = cur.fetchone()[0]
    conn.commit()
    conn.close()
    print(f"municipio: {len(linhas)} recebidos da API, {total} na tabela")


if __name__ == "__main__":
    main()
