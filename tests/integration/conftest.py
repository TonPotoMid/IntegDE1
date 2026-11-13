from decimal import Decimal

import pytest

from pipeline import db, storage
from pipeline.config import settings

TABLES = ["transactions", "sent_by_iban", "sent_by_bank", "received_by_iban", "processed_files"]


@pytest.fixture
def conn():
    with db.connect() as c:
        db.init_schema(c)
        yield c


@pytest.fixture
def s3():
    client = storage.get_client()
    storage.ensure_bucket(client)
    return client


@pytest.fixture
def clean_env(conn, s3):
    """Repart d'un état vide (DB + bucket)."""
    conn.execute(f"TRUNCATE {', '.join(TABLES)}")
    for key in storage.list_keys(s3, prefix=""):
        s3.delete_object(Bucket=settings.s3_bucket, Key=key)
    yield


def fetch_totals(conn, table: str, key_col: str) -> dict[str, Decimal]:
    return dict(conn.execute(f"SELECT {key_col}, total FROM {table}").fetchall())
