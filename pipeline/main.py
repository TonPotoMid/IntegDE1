"""Orchestration de la pipeline.

  python -m pipeline.main generate --output data   # génère les CSV
  python -m pipeline.main upload --input data      # pousse les CSV dans le S3
  python -m pipeline.main init-db                  # crée le schéma
  python -m pipeline.main process                  # S3 -> traitement -> DB
  python -m pipeline.main all                      # tout enchaîner
  python -m pipeline.main process --loop 60        # mode prod : rejoue toutes les 60 s
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from pipeline import db, storage
from pipeline.generate import generate
from pipeline.loader import checksum, parse_csv
from pipeline.processing import process

log = logging.getLogger("pipeline")


def cmd_upload(input_dir: str) -> list[str]:
    client = storage.get_client()
    storage.ensure_bucket(client)
    return [storage.upload_file(client, p) for p in sorted(Path(input_dir).glob("*.csv"))]


def cmd_init_db() -> None:
    with db.connect() as conn:
        db.init_schema(conn)


def cmd_process() -> dict[str, int]:
    """Traite tous les fichiers S3 non encore traités. Retourne des compteurs."""
    stats = {"processed": 0, "skipped": 0}
    client = storage.get_client()
    storage.ensure_bucket(client)
    with db.connect() as conn:
        db.init_schema(conn)
        keys = storage.list_keys(client)
        log.info("%d fichier(s) trouvé(s) dans le S3", len(keys))
        for key in keys:
            content = storage.download(client, key)
            digest = checksum(content)
            if db.is_processed(conn, key, digest):
                log.info("SKIP %s (déjà traité)", key)
                stats["skipped"] += 1
                continue
            result = process(parse_csv(content.decode("utf-8")))
            if db.insert_with_retry(key, digest, result):
                stats["processed"] += 1
            else:
                stats["skipped"] += 1
    log.info("Bilan: %s", stats)
    return stats


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--output", default="data")
    u = sub.add_parser("upload"); u.add_argument("--input", default="data")
    sub.add_parser("init-db")
    p = sub.add_parser("process"); p.add_argument("--loop", type=int, default=0, help="intervalle en secondes")
    a = sub.add_parser("all"); a.add_argument("--data-dir", default="data")
    args = parser.parse_args(argv)

    if args.cmd == "generate":
        for path in generate(args.output):
            log.info("Généré %s", path)
    elif args.cmd == "upload":
        cmd_upload(args.input)
    elif args.cmd == "init-db":
        cmd_init_db()
    elif args.cmd == "process":
        if args.loop:
            while True:  # planificateur simple pour la prod (niveau 3)
                try:
                    cmd_process()
                except Exception:  # noqa: BLE001 - on ne veut pas tuer le service
                    log.exception("Échec de l'itération, nouvel essai au prochain cycle")
                time.sleep(args.loop)
        cmd_process()
    elif args.cmd == "all":
        generate(args.data_dir)
        cmd_upload(args.data_dir)
        cmd_init_db()
        cmd_process()
    return 0


if __name__ == "__main__":
    sys.exit(main())
