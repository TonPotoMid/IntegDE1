"""Injection de pannes pour simuler des bugs (insertion DB / téléchargement S3).

Variables d'environnement :
  SIMULATE_INSERT_FAILURES=N    -> les N premières insertions échouent
  SIMULATE_DOWNLOAD_FAILURES=N  -> les N premiers téléchargements S3 échouent
"""
from __future__ import annotations

import os


class FaultInjector:
    def __init__(self, env_var: str):
        self.env_var = env_var
        self.remaining = int(os.getenv(env_var, "0"))

    def reset(self, count: int) -> None:
        self.remaining = count

    def maybe_fail(self, exc_factory) -> None:
        if self.remaining > 0:
            self.remaining -= 1
            raise exc_factory(f"[{self.env_var}] panne simulée (reste {self.remaining})")


insert_faults = FaultInjector("SIMULATE_INSERT_FAILURES")
download_faults = FaultInjector("SIMULATE_DOWNLOAD_FAILURES")
