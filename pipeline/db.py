"""Accès base de données : schéma, idempotence et insertion (avec retry)."""
from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from pipeline.config import settings
from pipeline.faults import insert_faults
from pipeline.models import ProcessingResult
from pipeline.retry import retry

log = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


@retry(attempts=10, delay=1.0, backoff=1.5, exceptions=(psycopg.OperationalError,))
def connect(database_url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(database_url or settings.database_url, autocommit=True)


def init_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    log.info("Schéma initialisé")


def is_processed(conn: psycopg.Connection, file_key: str, checksum: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM processed_files WHERE file_key = %s OR checksum = %s", (file_key, checksum)
    ).fetchone()
    return row is not None


def _upsert_totals(cur: psycopg.Cursor, table: str, key_col: str, totals: dict) -> None:
    cur.executemany(
        f"INSERT INTO {table} ({key_col}, total) VALUES (%s, %s) "
        f"ON CONFLICT ({key_col}) DO UPDATE SET total = {table}.total + EXCLUDED.total",
        list(totals.items()),
    )


def insert_results(conn: psycopg.Connection, file_key: str, checksum: str, result: ProcessingResult) -> bool:
    """Insère les résultats d'un fichier dans UNE transaction atomique.

    L'enregistrement dans processed_files est fait dans la même transaction : soit tout est
    inséré ET le fichier est marqué traité, soit rien (rollback) -> un retry ne double rien.
    Retourne False si le fichier avait déjà été traité.
    """
    with conn.transaction():
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO processed_files (file_key, checksum, row_count) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (file_key, checksum, len(result.transactions)),
        )
        if cur.rowcount == 0:
            log.info("%s déjà traité, ignoré", file_key)
            return False
        cur.executemany(
            "INSERT INTO transactions (transaction_id, datetime_transaction, iban_origine, pays_source, "
            "banque_source, iban_destinataire, pays_destinataire, montant, is_flagged, source_file) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    ft.transaction.transaction_id, ft.transaction.datetime_transaction,
                    ft.transaction.iban_origine, ft.transaction.pays_source, ft.transaction.banque_source,
                    ft.transaction.iban_destinataire, ft.transaction.pays_destinataire,
                    ft.transaction.montant, ft.is_flagged, file_key,
                )
                for ft in result.transactions
            ],
        )
        # Panne simulée APRÈS des écritures partielles : démontre le rollback.
        insert_faults.maybe_fail(psycopg.OperationalError)
        _upsert_totals(cur, "sent_by_iban", "iban", result.sent_by_iban)
        _upsert_totals(cur, "sent_by_bank", "banque", result.sent_by_bank)
        _upsert_totals(cur, "received_by_iban", "iban", result.received_by_iban)
    log.info("%s inséré (%d transactions)", file_key, len(result.transactions))
    return True


def insert_with_retry(file_key: str, checksum: str, result: ProcessingResult, database_url: str | None = None) -> bool:
    """Retry de l'insertion : nouvelle connexion à chaque tentative (la précédente peut être cassée)."""

    @retry(attempts=settings.retry_attempts, delay=settings.retry_delay, exceptions=(psycopg.OperationalError,))
    def insert_file() -> bool:
        with connect(database_url) as conn:
            return insert_results(conn, file_key, checksum, result)

    return insert_file()
