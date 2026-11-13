"""Fonctions de traitement PURES : aucune I/O, aucun état global, pas de mutation des entrées."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal

from pipeline.models import FlaggedTransaction, ProcessingResult, Transaction

FLAG_THRESHOLD = Decimal("5000")


def _sum_by(transactions: Iterable[Transaction], key: Callable[[Transaction], str]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for t in transactions:
        totals[key(t)] = totals.get(key(t), Decimal("0")) + t.montant
    return dict(sorted(totals.items()))


def sum_sent_by_iban(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    """Somme des montants envoyés par IBAN d'origine."""
    return _sum_by(transactions, lambda t: t.iban_origine)


def sum_sent_by_bank(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    """Somme des montants envoyés par banque source."""
    return _sum_by(transactions, lambda t: t.banque_source)


def sum_received_by_iban(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    """Somme des montants reçus par IBAN destinataire."""
    return _sum_by(transactions, lambda t: t.iban_destinataire)


def is_suspicious(transaction: Transaction, threshold: Decimal = FLAG_THRESHOLD) -> bool:
    """Une transaction est flaggée si son montant est STRICTEMENT au-dessus du seuil."""
    return transaction.montant > threshold


def flag_transactions(
    transactions: Iterable[Transaction], threshold: Decimal = FLAG_THRESHOLD
) -> tuple[FlaggedTransaction, ...]:
    return tuple(FlaggedTransaction(t, is_suspicious(t, threshold)) for t in transactions)


def process(transactions: Iterable[Transaction]) -> ProcessingResult:
    txs = tuple(transactions)
    return ProcessingResult(
        transactions=flag_transactions(txs),
        sent_by_iban=sum_sent_by_iban(txs),
        sent_by_bank=sum_sent_by_bank(txs),
        received_by_iban=sum_received_by_iban(txs),
    )
