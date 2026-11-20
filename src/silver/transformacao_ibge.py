from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BRONZE_DIR = Path("data/bronze")
SILVER_DIR = Path("data/silver")

def main():
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(BRONZE_DIR.glob("*.parquet"))

    if not arquivos:
        print("Nenhum ficheiro .parquet encontrado em data/bronze.")
        return

    data_processamento = datetime.now(timezone.utc).isoformat()

    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)
        df.columns = [col.strip().lower() for col in df.columns]
        df = df.drop_duplicates()
        df["processado_em_utc"] = data_processamento

        destino = SILVER_DIR / arquivo.name
        df.to_parquet(destino, index=False)
        print(f"OK Silver: {arquivo.name} -> {destino} ({len(df)} linhas)")

if __name__ == "__main__":
    main()
