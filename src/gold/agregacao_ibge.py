from pathlib import Path
import pandas as pd

SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")

def main():
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(SILVER_DIR.glob("*.parquet"))

    if not arquivos:
        print("Nenhum ficheiro .parquet encontrado em data/silver.")
        return

    resumo = []
    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)
        resumo.append({
            "tabela": arquivo.stem,
            "total_linhas": len(df),
            "total_colunas": len(df.columns),
        })

        # Se for populacao_municipio e tiver colunas de ano e populacao, cria visão agregada
        cols_lower = set(df.columns)
        if arquivo.stem == "populacao_municipio":
            col_ano = next((c for c in ["ano", "year"] if c in cols_lower), None)
            col_pop = next((c for c in ["populacao", "pop", "valor", "total"] if c in cols_lower), None)
            if col_ano and col_pop:
                df_agg = df.groupby(col_ano, dropna=False)[col_pop].sum().reset_index()
                destino_agg = GOLD_DIR / "gold_populacao_por_ano.parquet"
                df_agg.to_parquet(destino_agg, index=False)
                print(f"OK Gold: {destino_agg} ({len(df_agg)} linhas)")

    df_resumo = pd.DataFrame(resumo)
    destino_resumo = GOLD_DIR / "gold_resumo_camadas.parquet"
    df_resumo.to_parquet(destino_resumo, index=False)
    print(f"OK Gold: {destino_resumo} ({len(df_resumo)} linhas)")

if __name__ == "__main__":
    main()
