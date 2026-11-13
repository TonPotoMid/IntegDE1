"""Stockage S3 local (SeaweedFS) : upload, listing et récupération avec retry."""
from __future__ import annotations

import logging
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from pipeline.config import settings
from pipeline.faults import download_faults
from pipeline.retry import retry

log = logging.getLogger(__name__)
S3_ERRORS = (BotoCoreError, ClientError, ConnectionError)


class DownloadError(ConnectionError):
    pass


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 1}, connect_timeout=3, read_timeout=10),
    )


@retry(attempts=15, delay=1.0, backoff=1.3, exceptions=S3_ERRORS)
def ensure_bucket(client, bucket: str = settings.s3_bucket) -> None:
    existing = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if bucket not in existing:
        client.create_bucket(Bucket=bucket)
        log.info("Bucket %s créé", bucket)


@retry(attempts=settings.retry_attempts, delay=settings.retry_delay, exceptions=S3_ERRORS)
def upload_file(client, path: str | Path, bucket: str = settings.s3_bucket, prefix: str = settings.s3_prefix) -> str:
    key = f"{prefix}{Path(path).name}"
    client.upload_file(str(path), bucket, key)
    log.info("Upload %s -> s3://%s/%s", path, bucket, key)
    return key


def list_keys(client, bucket: str = settings.s3_bucket, prefix: str = settings.s3_prefix) -> list[str]:
    keys: list[str] = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".csv")]
    return sorted(keys)


@retry(attempts=settings.retry_attempts, delay=settings.retry_delay, exceptions=S3_ERRORS)
def download(client, key: str, bucket: str = settings.s3_bucket) -> bytes:
    """Récupère un fichier depuis S3 ; retry automatique si la récupération échoue."""
    download_faults.maybe_fail(DownloadError)
    return client.get_object(Bucket=bucket, Key=key)["Body"].read()
