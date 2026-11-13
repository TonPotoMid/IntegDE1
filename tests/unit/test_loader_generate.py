import csv

import pytest

from pipeline.generate import DATASET, generate
from pipeline.loader import InvalidCsvError, checksum, load_local, parse_csv
from pipeline.models import CSV_COLUMNS

HEADER = ",".join(CSV_COLUMNS)


def test_generate_is_deterministic(tmp_path):
    p1 = generate(tmp_path / "a")
    p2 = generate(tmp_path / "b")
    assert [checksum(load_local(x)) for x in p1] == [checksum(load_local(x)) for x in p2]


def test_generate_files_have_5_to_10_rows(tmp_path):
    paths = generate(tmp_path)
    assert len(paths) == len(DATASET) >= 2
    for p in paths:
        with p.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert 5 <= len(rows) <= 10
        assert list(rows[0].keys()) == CSV_COLUMNS


def test_generated_ids_are_unique(tmp_path):
    ids = [t.transaction_id for p in generate(tmp_path) for t in parse_csv(p.read_text(encoding="utf-8"))]
    assert len(ids) == len(set(ids))


def test_parse_csv_ok(tmp_path):
    p = generate(tmp_path)[0]
    txs = parse_csv(p.read_text(encoding="utf-8"))
    assert txs[0].transaction_id == "T001"
    assert str(txs[0].montant) == "1200.00"


@pytest.mark.parametrize(
    "content",
    [
        "a,b,c\n1,2,3\n",  # mauvaises colonnes
        HEADER + "\n",  # vide
        HEADER + "\nT1,2026-01-01T00:00:00,X,FR,Bk,Y,FR,abc\n",  # montant invalide
        HEADER + "\nT1,2026-01-01T00:00:00,X,FR,Bk,Y,FR,-5\n",  # montant négatif
        HEADER + "\nT1,pas-une-date,X,FR,Bk,Y,FR,5\n",  # date invalide
        HEADER + "\nT1,2026-01-01T00:00:00,,FR,Bk,Y,FR,5\n",  # champ vide
    ],
)
def test_parse_csv_rejects_invalid(content):
    with pytest.raises(InvalidCsvError):
        parse_csv(content)
