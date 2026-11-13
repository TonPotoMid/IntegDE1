from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://pipeline:pipeline@localhost:5432/transactions")
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "http://localhost:8333")
    s3_bucket: str = os.getenv("S3_BUCKET", "transactions")
    s3_prefix: str = os.getenv("S3_PREFIX", "incoming/")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", "admin")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", "admin-secret")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    retry_attempts: int = int(os.getenv("RETRY_ATTEMPTS", "4"))
    retry_delay: float = float(os.getenv("RETRY_DELAY", "0.5"))


settings = Settings()
