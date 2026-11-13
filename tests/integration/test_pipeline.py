"""Tests d'intégration bout-en-bout : S3 (SeaweedFS) + PostgreSQL réels."""
import psycopg
import pytest

from pipeline import main, storage
from pipeline.config import settings
from pipeline.faults import download_faults, insert_faults
from tests import expected
from tests.integration.conftest import fetch_totals


def _assert_expected_state(conn):
    count, total = conn.execute("SELECT count(*), sum(montant) FROM transactions").fetchone()
    assert count == expected.TOTAL_TRANSACTIONS
    assert total == expected.TOTAL_AMOUNT
    assert fetch_totals(conn, "sent_by_iban", "iban") == expected.SENT_BY_IBAN
    assert fetch_totals(conn, "sent_by_bank", "banque") == expected.SENT_BY_BANK
    assert fetch_totals(conn, "received_by_iban", "iban") == expected.RECEIVED_BY_IBAN
    flagged = {r[0] for r in conn.execute("SELECT transaction_id FROM transactions WHERE is_flagged")}
    assert flagged == expected.FLAGGED_IDS


@pytest.fixture
def uploaded(clean_env, tmp_path):
    main.generate(tmp_path)
    keys = main.cmd_upload(str(tmp_path))
    assert len(keys) == 3
    return tmp_path


def test_full_pipeline(uploaded, conn):
    assert main.cmd_process() == {"processed": 3, "skipped": 0}
    _assert_expected_state(conn)


def test_rerun_does_not_reprocess(uploaded, conn):
    main.cmd_process()
    assert main.cmd_process() == {"processed": 0, "skipped": 3}
    _assert_expected_state(conn)  # aucune valeur doublée


def test_same_content_under_new_name_is_skipped(uploaded, conn, s3):
    main.cmd_process()
    s3.upload_file(str(uploaded / "transactions_2026-11-01.csv"), settings.s3_bucket, "incoming/copie.csv")
    assert main.cmd_process()["processed"] == 0
    _assert_expected_state(conn)


def test_new_file_is_processed_incrementally(clean_env, conn, s3, tmp_path):
    paths = main.generate(tmp_path)
    storage.upload_file(s3, paths[0])
    assert main.cmd_process()["processed"] == 1
    for p in paths[1:]:
        storage.upload_file(s3, p)
    assert main.cmd_process() == {"processed": 2, "skipped": 1}
    _assert_expected_state(conn)


def test_insert_failure_is_retried_without_duplicates(uploaded, conn):
    """Bug d'insertion simulé : 2 échecs puis succès. Le rollback garantit l'absence de doublon."""
    insert_faults.reset(2)
    assert main.cmd_process()["processed"] == 3
    assert insert_faults.remaining == 0
    _assert_expected_state(conn)


def test_insert_failure_exhausted_then_recovered(uploaded, conn):
    """Toutes les tentatives échouent : rien n'est inséré (rollback), le run suivant rattrape."""
    insert_faults.reset(settings.retry_attempts)
    with pytest.raises(psycopg.OperationalError):
        main.cmd_process()
    assert conn.execute("SELECT count(*) FROM processed_files").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 0
    insert_faults.reset(0)
    assert main.cmd_process()["processed"] == 3
    _assert_expected_state(conn)


def test_download_failure_is_retried(uploaded, conn):
    download_faults.reset(settings.retry_attempts - 1)
    assert main.cmd_process()["processed"] == 3
    assert download_faults.remaining == 0
    _assert_expected_state(conn)
