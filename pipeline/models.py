"""Modèle de données d'une transaction financière."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

CSV_COLUMNS = [
    "transaction_id",
    "datetime_transaction",
    "iban_origine",
    "pays_source",
    "banque_source",
    "iban_destinataire",
    "pays_destinataire",
    "montant",
]


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    datetime_transaction: datetime
    iban_origine: str
    pays_source: str
    banque_source: str
    iban_destinataire: str
    pays_destinataire: str
    montant: Decimal


@dataclass(frozen=True)
class FlaggedTransaction:
    transaction: Transaction
    is_flagged: bool


@dataclass(frozen=True)
class ProcessingResult:
    """Résultat (immuable) du traitement d'un fichier."""

    transactions: tuple[FlaggedTransaction, ...]
    sent_by_iban: dict[str, Decimal]
    sent_by_bank: dict[str, Decimal]
    received_by_iban: dict[str, Decimal]
