"""Chargement des données (séparé du traitement)."""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pipeline.models import CSV_COLUMNS, Transaction


class InvalidCsvError(ValueError):
    pass


def checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_csv(content: str) -> list[Transaction]:
    """Parse et valide le contenu d'un CSV de transactions."""
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames != CSV_COLUMNS:
        raise InvalidCsvError(f"Colonnes inattendues: {reader.fieldnames}, attendu {CSV_COLUMNS}")

    transactions: list[Transaction] = []
    for line_no, row in enumerate(reader, start=2):
        try:
            montant = Decimal(row["montant"])
            dt = datetime.fromisoformat(row["datetime_transaction"])
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidCsvError(f"Ligne {line_no} invalide: {row}") from exc
        if montant <= 0:
            raise InvalidCsvError(f"Ligne {line_no}: montant non positif ({montant})")
        if any(not (row[c] or "").strip() for c in CSV_COLUMNS):
            raise InvalidCsvError(f"Ligne {line_no}: champ vide ({row})")
        transactions.append(
            Transaction(
                transaction_id=row["transaction_id"],
                datetime_transaction=dt,
                iban_origine=row["iban_origine"],
                pays_source=row["pays_source"],
                banque_source=row["banque_source"],
                iban_destinataire=row["iban_destinataire"],
                pays_destinataire=row["pays_destinataire"],
                montant=montant,
            )
        )
    if not transactions:
        raise InvalidCsvError("Fichier CSV vide")
    return transactions


def load_local(path: str | Path) -> bytes:
    return Path(path).read_bytes()
