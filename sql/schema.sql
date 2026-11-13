-- Schéma relationnel des résultats de traitement

-- Journal des fichiers traités : garantit qu'un fichier n'est jamais traité deux fois
-- (clé = nom du fichier, et le checksum est unique pour détecter un même contenu renommé).
CREATE TABLE IF NOT EXISTS processed_files (
    file_key      TEXT PRIMARY KEY,
    checksum      CHAR(64) NOT NULL UNIQUE,
    row_count     INTEGER NOT NULL CHECK (row_count > 0),
    processed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id        TEXT PRIMARY KEY,
    datetime_transaction  TIMESTAMP NOT NULL,
    iban_origine          TEXT NOT NULL,
    pays_source           CHAR(2) NOT NULL,
    banque_source         TEXT NOT NULL,
    iban_destinataire     TEXT NOT NULL,
    pays_destinataire     CHAR(2) NOT NULL,
    montant               NUMERIC(14, 2) NOT NULL CHECK (montant > 0),
    is_flagged            BOOLEAN NOT NULL,
    source_file           TEXT NOT NULL REFERENCES processed_files(file_key)
);
CREATE INDEX IF NOT EXISTS idx_transactions_flagged ON transactions(is_flagged);

-- Agrégats (mis à jour de façon incrémentale, fichier par fichier)
CREATE TABLE IF NOT EXISTS sent_by_iban (
    iban   TEXT PRIMARY KEY,
    total  NUMERIC(16, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS sent_by_bank (
    banque TEXT PRIMARY KEY,
    total  NUMERIC(16, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS received_by_iban (
    iban   TEXT PRIMARY KEY,
    total  NUMERIC(16, 2) NOT NULL
);
