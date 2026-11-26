import os
import psycopg2

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ibge_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ibge_origem")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")

conn = psycopg2.connect(
    dbname=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
)

import csv
import io

cur = conn.cursor()

cur.execute("""
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public';
""")

csv_files = {}

tables = cur.fetchall()

for (table,) in tables:
    buffer = io.StringIO()
    cur.execute(f'SELECT * FROM "{table}"')
    writer = csv.writer(buffer)
    writer.writerow([desc[0] for desc in cur.description])
    writer.writerows(cur.fetchall())
    csv_files[f"{table}.csv"] = buffer.getvalue()
    buffer.close()

cur.close()
conn.close()

import boto3
from botocore.config import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT") or "http://lakehouse_minio:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("MINIO_SECRET_KEY", "minioadmin123")

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
    config=Config(s3={"addressing_style": "path"}),
)

bucket_name = "landing"

for filename, content in csv_files.items():

    s3_client.put_object(
        Bucket=bucket_name,
        Key=f"{filename}",
        Body=content.encode("utf-8"),
        ContentType="text/csv"
    )

    print(f"Uploaded: {filename}")
