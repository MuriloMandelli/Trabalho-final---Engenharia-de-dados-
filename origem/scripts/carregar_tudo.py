"""Roda todas as cargas na ordem certa e mostra um resumo no final.

Uso (dentro da pasta origem, com o ambiente virtual ativo):  python scripts/carregar_tudo.py
Se uma etapa falhar, as outras continuam e o resumo mostra qual precisa de atenção.
A etapa da PNAD só roda se os arquivos estiverem em origem/dados/ (veja scripts/carga_pnad.py).
"""
import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parent

ETAPAS = [
    ("Municípios (achatados)", ["carga_localidades.py"]),
    ("IPCA", ["carga_indice_precos.py", "ipca", "--reservar", "1"]),
    ("INPC", ["carga_indice_precos.py", "inpc", "--reservar", "1"]),
    ("População", ["carga_populacao.py"]),
    ("PIB dos municípios", ["carga_sidra.py", "pib"]),
    ("Produção agrícola", ["carga_sidra.py", "agricola"]),
    ("Rebanhos", ["carga_sidra.py", "rebanho"]),
    ("Produção de origem animal", ["carga_sidra.py", "origem_animal"]),
    ("PNAD Contínua (microdados)", ["carga_pnad.py"]),
]


def main():
    resultado = []
    for nome, comando in ETAPAS:
        print("\n" + "=" * 70 + f"\n{nome}\n" + "=" * 70)
        if comando[0] == "carga_pnad.py" and not list((RAIZ / "dados").glob("PNADC_*.zip")):
            print("Pulei: nenhum PNADC_*.zip em origem/dados/ (baixe os arquivos e rode carga_pnad.py depois).")
            resultado.append((nome, "PULADA"))
            continue
        codigo = subprocess.run([sys.executable, str(PASTA / comando[0]), *comando[1:]], cwd=RAIZ).returncode
        resultado.append((nome, "ok" if codigo == 0 else f"FALHOU (código {codigo})"))

    print("\n" + "=" * 70 + "\nRESUMO\n" + "=" * 70)
    for nome, status in resultado:
        print(f"  {nome:32s} {status}")
    print("\nConfira os números com origem/consultas/validacao.sql no DBeaver.")


if __name__ == "__main__":
    main()
