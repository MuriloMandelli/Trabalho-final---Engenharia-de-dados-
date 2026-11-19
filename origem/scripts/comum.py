"""Funções compartilhadas pelos scripts de carga."""
import os
import re
import time
import unicodedata
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

# Lê o arquivo origem/.env (se existir)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

RAIZ = Path(__file__).resolve().parent.parent


def conectar():
    """Abre conexão com o PostgreSQL de origem."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "ibge_origem"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "admin"),
    )


def get(url, params=None, tentativas=3):
    """GET em JSON com novas tentativas em caso de falha."""
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, params=params, timeout=120)
            if resp.status_code >= 400:
                print(f"  resposta da API: {resp.text[:300]}")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as erro:
            print(f"  tentativa {tentativa}/{tentativas} falhou: {erro}")
            if tentativa == tentativas:
                raise
            time.sleep(3 * tentativa)


def converter(valor):
    """Converte o texto da API em número. '-', '...', 'X' viram None."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def slug(texto, limite=50):
    """'Área plantada (ha)' -> 'area_plantada_ha' (nome de coluna seguro)."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower()
    if not t or t[0].isdigit():
        t = "v_" + t
    return t[:limite].rstrip("_")
