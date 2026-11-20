import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

DB_HOST = os.getenv("IBGE_DB_HOST", "localhost")
DB_PORT = os.getenv("IBGE_DB_PORT", "5432")
DB_NAME = os.getenv("IBGE_DB_NAME", "ibge_origem")
DB_USER = os.getenv("IBGE_DB_USER", "admin")
DB_PASS = os.getenv("IBGE_DB_PASS", "admin")

TABELAS_IBGE = [
    "municipio",
    "categoria_produto",
    "ipca_valor",
    "inpc_valor",
    "populacao_municipio",
    "pib_municipio",
    "producao_agricola",
    "rebanho_municipio",
    "producao_origem_animal",
]

def main():
    saída_base = Path("data/bronze")
    saída_base.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    for tabela in TABELAS_IBGE:
        df = pd.read_sql(f"SELECT * FROM public.{tabela}", engine)
        destino = saída_base / f"{tabela}.parquet"
        df.to_parquet(destino, index=False)
        print(f"OK: {tabela} -> {destino} ({len(df)} linhas)")

if __name__ == "__main__":
    main()
