import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from txpipe.models import ProcessingResults, Transaction

SCHEMA = """
CREATE TABLE IF NOT EXISTS fichiers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nom             TEXT    NOT NULL,
    sha256          TEXT    NOT NULL UNIQUE,
    nb_transactions INTEGER NOT NULL CHECK (nb_transactions > 0),
    traite_le       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    fichier_id           INTEGER NOT NULL REFERENCES fichiers(id),
    datetime_transaction TEXT    NOT NULL,
    iban_origine         TEXT    NOT NULL,
    pays_source          TEXT    NOT NULL,
    banque_source        TEXT    NOT NULL,
    iban_destinataire    TEXT    NOT NULL,
    pays_destinataire    TEXT    NOT NULL,
    montant_centimes     INTEGER NOT NULL CHECK (montant_centimes > 0),
    devise               TEXT    NOT NULL,
    depasse_seuil        INTEGER NOT NULL CHECK (depasse_seuil IN (0, 1))
);

CREATE TABLE IF NOT EXISTS agregats (
    fichier_id     INTEGER NOT NULL REFERENCES fichiers(id),
    type           TEXT    NOT NULL CHECK (type IN ('envoye_par_iban', 'envoye_par_banque', 'recu_par_iban')),
    cle            TEXT    NOT NULL,
    total_centimes INTEGER NOT NULL,
    PRIMARY KEY (fichier_id, type, cle)
);
"""


def to_centimes(montant: Decimal) -> int:
    """Decimal('12.30') -> 1230. Exact car le loader a refusé plus de 2 décimales."""
    return int((montant * 100).to_integral_exact())


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def _insert_transactions(
    conn: sqlite3.Connection,
    fichier_id: int,
    transactions: Sequence[Transaction],
    flags: Sequence[bool],
) -> None:
    conn.executemany(
        "INSERT INTO transactions (fichier_id, datetime_transaction, iban_origine, pays_source,"
        " banque_source, iban_destinataire, pays_destinataire, montant_centimes, devise, depasse_seuil)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                fichier_id,
                tx["datetime_transaction"].isoformat(),
                tx["iban_origine"],
                tx["pays_source"],
                tx["banque_source"],
                tx["iban_destinataire"],
                tx["pays_destinataire"],
                to_centimes(tx["montant"]),
                tx["devise"],
                int(flag),
            )
            for tx, flag in zip(transactions, flags, strict=True)
        ],
    )


def _insert_aggregates(
    conn: sqlite3.Connection,
    fichier_id: int,
    results: ProcessingResults,
) -> None:
    lignes: list[tuple[int, str, str, int]] = []
    for cle, total in results.sent_by_iban.items():
        lignes.append((fichier_id, "envoye_par_iban", cle, to_centimes(total)))
    for cle, total in results.sent_by_bank.items():
        lignes.append((fichier_id, "envoye_par_banque", cle, to_centimes(total)))
    for cle, total in results.received_by_iban.items():
        lignes.append((fichier_id, "recu_par_iban", cle, to_centimes(total)))
    conn.executemany(
        "INSERT INTO agregats (fichier_id, type, cle, total_centimes) VALUES (?, ?, ?, ?)",
        lignes,
    )


def insert_file(
    conn: sqlite3.Connection,
    *,
    name: str,
    sha256: str,
    transactions: Sequence[Transaction],
    results: ProcessingResults,
) -> bool:
    """Insère UN fichier de façon atomique : tout est écrit, ou rien.

    Retourne True si le fichier a été inséré, False s'il l'était déjà (même sha256).
    """
    if not transactions:
        raise ValueError("insert_file: aucune transaction")

  
    conn.execute("BEGIN IMMEDIATE")
    try:
        deja = conn.execute("SELECT 1 FROM fichiers WHERE sha256 = ?", (sha256,)).fetchone()
        if deja is not None:
            conn.execute("ROLLBACK") 
            return False

        cursor = conn.execute(
            "INSERT INTO fichiers (nom, sha256, nb_transactions, traite_le) VALUES (?, ?, ?, ?)",
            (name, sha256, len(transactions), datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        fichier_id = cursor.lastrowid
        if fichier_id is None:
            raise sqlite3.DatabaseError("pas d'identifiant de fichier retourné")

        _insert_transactions(conn, fichier_id, transactions, results.over_threshold)
        _insert_aggregates(conn, fichier_id, results)
        conn.execute("COMMIT") 
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")  
        raise
    return True