# apps/api/app/storage.py
import hashlib
from typing import Tuple
import boto3
from botocore.client import Config
from .settings import settings

def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name=settings.s3_region or "us-east-1",
    )

def put_pdf_and_sha(key: str, pdf_bytes: bytes) -> Tuple[str, str]:
    """Uploads bytes to the configured bucket and returns (s3_url, sha256_hex)."""
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    s3 = _s3()
    # Create bucket if it doesn't exist (idempotent in MinIO)
    try:
        s3.create_bucket(Bucket=settings.s3_bucket)
    except Exception:
        pass

    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
        Metadata={"sha256": sha256},
    )
    return f"s3://{settings.s3_bucket}/{key}", sha256
