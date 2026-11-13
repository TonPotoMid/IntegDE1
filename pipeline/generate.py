"""Génération de CSV de transactions DÉTERMINISTES (pas d'aléatoire -> pipeline testable)."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pipeline.models import CSV_COLUMNS

# IBAN -> (pays, banque)
ACCOUNTS = {
    "FR7630006000011234567890189": ("FR", "BNP Paribas"),
    "FR7630004000031234567890143": ("FR", "BNP Paribas"),
    "DE89370400440532013000": ("DE", "Deutsche Bank"),
    "ES9121000418450200051332": ("ES", "CaixaBank"),
    "IT60X0542811101000000123456": ("IT", "UniCredit"),
    "FR1420041010050500013M02606": ("FR", "La Banque Postale"),
}
A, F, B, C, D, E = ACCOUNTS.keys()

# (id, datetime, origine, destinataire, montant)
DATASET: dict[str, list[tuple[str, str, str, str, str]]] = {
    "transactions_2026-11-01.csv": [
        ("T001", "2026-11-01T09:00:00", A, B, "1200.00"),
        ("T002", "2026-11-01T10:30:00", B, C, "7500.00"),
        ("T003", "2026-11-01T11:15:00", C, A, "300.50"),
        ("T004", "2026-11-01T14:00:00", A, D, "5000.00"),
        ("T005", "2026-11-01T16:45:00", D, E, "250.00"),
    ],
    "transactions_2026-11-02.csv": [
        ("T006", "2026-11-02T08:10:00", E, A, "980.00"),
        ("T007", "2026-11-02T09:20:00", A, C, "15000.00"),
        ("T008", "2026-11-02T10:05:00", B, D, "640.25"),
        ("T009", "2026-11-02T12:40:00", C, E, "5000.01"),
        ("T010", "2026-11-02T15:30:00", D, B, "75.75"),
        ("T011", "2026-11-02T17:55:00", F, B, "2100.00"),
    ],
    "transactions_2026-11-03.csv": [
        ("T012", "2026-11-03T08:00:00", A, E, "450.00"),
        ("T013", "2026-11-03T09:45:00", B, A, "3200.00"),
        ("T014", "2026-11-03T11:00:00", C, D, "12500.00"),
        ("T015", "2026-11-03T13:20:00", D, A, "820.00"),
        ("T016", "2026-11-03T14:10:00", F, C, "60.00"),
        ("T017", "2026-11-03T16:00:00", A, B, "999.99"),
        ("T018", "2026-11-03T18:30:00", B, E, "5400.00"),
    ],
}


def build_rows(entries: list[tuple[str, str, str, str, str]]) -> list[dict[str, str]]:
    rows = []
    for tx_id, dt, origin, dest, amount in entries:
        rows.append(
            {
                "transaction_id": tx_id,
                "datetime_transaction": dt,
                "iban_origine": origin,
                "pays_source": ACCOUNTS[origin][0],
                "banque_source": ACCOUNTS[origin][1],
                "iban_destinataire": dest,
                "pays_destinataire": ACCOUNTS[dest][0],
                "montant": amount,
            }
        )
    return rows


def generate(output_dir: str | Path) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, entries in DATASET.items():
        path = out / filename
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(build_rows(entries))
        paths.append(path)
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data")
    args = parser.parse_args()
    for p in generate(args.output):
        print(p)
