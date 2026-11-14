#!/bin/bash
set -e

# Start PostgreSQL using the official entrypoint
docker-entrypoint.sh postgres &

POSTGRES_PID=$!

# Wait until PostgreSQL is ready
until pg_isready -h localhost -p 5432; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo "PostgreSQL is ready!"

# Execute Python ingestion scripts
echo "Loading localities..."
python3 scripts/carga_localidades.py

echo "Loading IPCA..."
python3 scripts/carga_indice_precos.py ipca

echo "Loading INPC..."
python3 scripts/carga_indice_precos.py inpc

echo "Loading population..."
python3 scripts/carga_populacao.py

echo "Data ingestion completed!"

# Keep PostgreSQL running
wait $POSTGRES_PID
