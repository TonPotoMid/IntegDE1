from datetime import datetime
from decimal import Decimal

from pipeline.generate import DATASET, build_rows
from pipeline.models import Transaction
from pipeline.processing import (
    flag_transactions,
    is_suspicious,
    process,
    sum_received_by_iban,
    sum_sent_by_bank,
    sum_sent_by_iban,
)
from tests import expected


def _all_transactions() -> list[Transaction]:
    txs = []
    for entries in DATASET.values():
        for r in build_rows(entries):
            txs.append(Transaction(**{**r, "datetime_transaction": datetime.fromisoformat(r["datetime_transaction"]),
                                      "montant": Decimal(r["montant"])}))
    return txs


def _tx(montant: str, origin="X", dest="Y", bank="Bk") -> Transaction:
    return Transaction("T", datetime(2026, 1, 1), origin, "FR", bank, dest, "FR", Decimal(montant))


def test_sum_sent_by_iban():
    assert sum_sent_by_iban(_all_transactions()) == expected.SENT_BY_IBAN


def test_sum_sent_by_bank():
    assert sum_sent_by_bank(_all_transactions()) == expected.SENT_BY_BANK


def test_sum_received_by_iban():
    assert sum_received_by_iban(_all_transactions()) == expected.RECEIVED_BY_IBAN


def test_flag_threshold_is_strict():
    assert not is_suspicious(_tx("5000.00"))
    assert is_suspicious(_tx("5000.01"))
    assert not is_suspicious(_tx("4999.99"))


def test_flagged_ids():
    flagged = {ft.transaction.transaction_id for ft in flag_transactions(_all_transactions()) if ft.is_flagged}
    assert flagged == expected.FLAGGED_IDS


def test_totals_are_consistent():
    txs = _all_transactions()
    assert len(txs) == expected.TOTAL_TRANSACTIONS
    assert sum(sum_sent_by_iban(txs).values()) == expected.TOTAL_AMOUNT
    assert sum(sum_received_by_iban(txs).values()) == expected.TOTAL_AMOUNT


def test_process_is_pure():
    txs = [_tx("100", "A"), _tx("6000", "A")]
    snapshot = list(txs)
    r1, r2 = process(txs), process(txs)
    assert r1 == r2
    assert txs == snapshot
    assert r1.sent_by_iban == {"A": Decimal("6100")}


def test_process_empty():
    r = process([])
    assert r.transactions == () and r.sent_by_iban == {}
