"""Vérifie l'état de la base APRÈS l'exécution de la pipeline (étape CI `pipeline.main all`).

Ce test ne nettoie rien : il contrôle ce que la pipeline a réellement inséré.
"""
from tests import expected
from tests.integration.conftest import fetch_totals


def test_all_files_processed_once(conn):
    rows = conn.execute("SELECT file_key, row_count FROM processed_files ORDER BY file_key").fetchall()
    assert rows == [
        ("incoming/transactions_2026-11-01.csv", 5),
        ("incoming/transactions_2026-11-02.csv", 6),
        ("incoming/transactions_2026-11-03.csv", 7),
    ]


def test_transactions_inserted(conn):
    count, total = conn.execute("SELECT count(*), sum(montant) FROM transactions").fetchone()
    assert count == expected.TOTAL_TRANSACTIONS
    assert total == expected.TOTAL_AMOUNT


def test_flags(conn):
    flagged = {r[0] for r in conn.execute("SELECT transaction_id FROM transactions WHERE is_flagged")}
    assert flagged == expected.FLAGGED_IDS


def test_aggregates(conn):
    assert fetch_totals(conn, "sent_by_iban", "iban") == expected.SENT_BY_IBAN
    assert fetch_totals(conn, "sent_by_bank", "banque") == expected.SENT_BY_BANK
    assert fetch_totals(conn, "received_by_iban", "iban") == expected.RECEIVED_BY_IBAN
