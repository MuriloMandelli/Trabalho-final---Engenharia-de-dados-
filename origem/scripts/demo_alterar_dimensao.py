"""Altera registros de DIMENSÃO no banco de origem, para demonstrar o SCD tipo 2.

Uso (dentro da pasta origem):
    python scripts/demo_alterar_dimensao.py             # muda o nome de um município e de um grupo de produtos
    python scripts/demo_alterar_dimensao.py --reverter  # volta ao nome original

O gatilho do banco atualiza "atualizado_em" automaticamente, e é isso que o pipeline
usa para detectar a mudança e fechar/abrir versões da dimensão (SCD tipo 2).
"""
import sys

from comum import conectar

SUFIXO = " (SCD2 teste)"

ALVOS = [
    ("municipio", "SELECT id FROM municipio WHERE id = 4204608"),  # Criciúma-SC
    ("categoria_produto", "SELECT id FROM categoria_produto WHERE nivel = 'grupo' ORDER BY id LIMIT 1"),
]


def main():
    reverter = "--reverter" in sys.argv
    conn = conectar()
    with conn.cursor() as cur:
        for tabela, consulta in ALVOS:
            cur.execute(consulta)
            linha = cur.fetchone()
            if not linha:
                print(f"{tabela}: nenhum registro encontrado, pulei.")
                continue
            registro_id = linha[0]
            if reverter:
                cur.execute(f"UPDATE {tabela} SET nome = replace(nome, %s, '') WHERE id = %s",
                            (SUFIXO, registro_id))
            else:
                cur.execute(f"UPDATE {tabela} SET nome = nome || %s WHERE id = %s AND nome NOT LIKE %s",
                            (SUFIXO, registro_id, "%" + SUFIXO))
            cur.execute(f"SELECT id, nome, atualizado_em FROM {tabela} WHERE id = %s", (registro_id,))
            print(tabela, cur.fetchone())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
