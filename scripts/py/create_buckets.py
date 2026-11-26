import os
import boto3
from botocore.config import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://lakehouse_minio:9000")
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

buckets = ['landing', 'bronze', 'silver', 'gold']


for currentBucket in buckets:   
    try:
        s3_client.head_bucket(Bucket=currentBucket)
        print(f"Bucket '{currentBucket}' já existe.")
    except Exception:
        s3_client.create_bucket(Bucket=currentBucket)
        print(f"Bucket '{currentBucket}' criado com sucesso.")

