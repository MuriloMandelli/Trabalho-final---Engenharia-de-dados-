"""Gera o diagrama do banco (formato DBML) a partir do banco REAL.

Uso (dentro da pasta origem):  python scripts/gerar_dbml.py
Escreve origem/modelo_origem.dbml. Cole o conteúdo em https://dbdiagram.io/d para ver o diagrama.
"""
from collections import defaultdict

from comum import RAIZ, conectar

SQL_COLUNAS = """
SELECT table_name, column_name, data_type, character_maximum_length,
       numeric_precision, numeric_scale, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position
"""

SQL_PK = """
SELECT kcu.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'
ORDER BY kcu.table_name, kcu.ordinal_position
"""

SQL_FK = """
SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text, af.attname
FROM pg_constraint c
JOIN LATERAL unnest(c.conkey, c.confkey) AS k(attnum, fattnum) ON true
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = k.fattnum
WHERE c.contype = 'f' AND c.connamespace = 'public'::regnamespace
ORDER BY 1, 2
"""

TIPOS = {
    "character varying": "varchar", "character": "char", "integer": "int", "smallint": "smallint",
    "bigint": "bigint", "numeric": "numeric", "text": "text", "date": "date",
    "timestamp without time zone": "timestamp",
}


def tipo_dbml(tipo, tamanho, precisao, escala):
    nome = TIPOS.get(tipo, tipo.replace(" ", "_"))
    if nome in ("varchar", "char") and tamanho:
        return f"{nome}({tamanho})"
    if nome == "numeric" and precisao:
        return f"numeric({precisao},{escala or 0})"
    return nome


def montar_dbml(colunas, pks, fks):
    """colunas: [(tabela, coluna, tipo, tam, prec, escala, nulo)], pks: [(tabela, coluna)], fks: [(t, c, t_ref, c_ref)]."""
    por_tabela = defaultdict(list)
    for tabela, coluna, tipo, tam, prec, esc, nulo in colunas:
        por_tabela[tabela].append((coluna, tipo_dbml(tipo, tam, prec, esc), nulo))
    chaves = defaultdict(list)
    for tabela, coluna in pks:
        chaves[tabela].append(coluna)
    refs = defaultdict(dict)
    for tabela, coluna, tabela_ref, coluna_ref in fks:
        refs[tabela][coluna] = f"{tabela_ref}.{coluna_ref}"

    saida = ["// Gerado por scripts/gerar_dbml.py. Cole em https://dbdiagram.io/d", ""]
    for tabela, cols in por_tabela.items():
        saida.append(f"Table {tabela} {{")
        for coluna, tipo, nulo in cols:
            opcoes = []
            if len(chaves[tabela]) == 1 and chaves[tabela][0] == coluna:
                opcoes.append("pk")
            if nulo == "NO":
                opcoes.append("not null")
            if coluna in refs[tabela]:
                opcoes.append(f"ref: > {refs[tabela][coluna]}")
            sufixo = f" [{', '.join(opcoes)}]" if opcoes else ""
            saida.append(f"  {coluna} {tipo}{sufixo}")
        if len(chaves[tabela]) > 1:
            saida += ["", "  indexes {", f"    ({', '.join(chaves[tabela])}) [pk]", "  }"]
        saida += ["}", ""]
    return "\n".join(saida)


def main():
    conn = conectar()
    with conn.cursor() as cur:
        cur.execute(SQL_COLUNAS)
        colunas = cur.fetchall()
        cur.execute(SQL_PK)
        pks = cur.fetchall()
        cur.execute(SQL_FK)
        fks = cur.fetchall()
    conn.close()
    destino = RAIZ / "modelo_origem.dbml"
    destino.write_text(montar_dbml(colunas, pks, fks), encoding="utf-8")
    print(f"Diagrama gerado em {destino}")


if __name__ == "__main__":
    main()
