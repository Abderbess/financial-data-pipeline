import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

import pytest

from txpipe import db
from txpipe.loader import CSV_COLUMNS, load_transactions
from txpipe.models import ProcessingResults, Transaction
from txpipe.pipeline import run
from txpipe.processing import compute_results
from txpipe.retry import retry

HEADER = ",".join(CSV_COLUMNS)
CSV_GOOD = f"""{HEADER}
2024-03-01T09:12:00,FR_A,FR,BNP,DE_X,DE,1250.00,EUR
2024-03-01T10:45:00,FR_A,FR,BNP,ES_Y,ES,7400.50,EUR
2024-03-01T11:00:00,GB_B,GB,NATWEST,DE_X,DE,100.10,EUR
"""


def count_transactions(db_path: Path) -> int:
    with closing(db.connect(db_path)) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])


def test_pipeline_recovers_from_a_transient_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """La 1re insertion échoue (base verrouillée), la 2e aboutit : le fichier est inséré UNE fois."""
    data, db_path = tmp_path / "data", tmp_path / "p.db"
    data.mkdir()
    (data / "a.csv").write_text(CSV_GOOD, encoding="utf-8")
    real_insert = db.insert_file
    calls: list[int] = []

    def flaky_insert(
        conn: sqlite3.Connection,
        *,
        name: str,
        sha256: str,
        transactions: Sequence[Transaction],
        results: ProcessingResults,
    ) -> bool:
        calls.append(1)
        if len(calls) == 1:
            raise sqlite3.OperationalError("database is locked")  # erreur transitoire simulée
        return real_insert(conn, name=name, sha256=sha256, transactions=transactions, results=results)

    monkeypatch.setattr(db, "insert_file", flaky_insert)

    code = run(data, db_path, generate=False, out=lambda _l: None, sleep=lambda _s: None)

    assert code == 0
    assert len(calls) == 2  # 1 échec + 1 réinsertion réussie
    assert count_transactions(db_path) == 3  # inséré une seule fois


def test_pipeline_does_not_retry_an_integrity_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data, db_path = tmp_path / "data", tmp_path / "p.db"
    data.mkdir()
    (data / "a.csv").write_text(CSV_GOOD, encoding="utf-8")
    calls: list[int] = []

    def violating_insert(
        conn: sqlite3.Connection,
        *,
        name: str,
        sha256: str,
        transactions: Sequence[Transaction],
        results: ProcessingResults,
    ) -> bool:
        calls.append(1)
        raise sqlite3.IntegrityError("CHECK constraint failed")

    monkeypatch.setattr(db, "insert_file", violating_insert)

    code = run(data, db_path, generate=False, out=lambda _l: None, sleep=lambda _s: None)

    assert code != 0
    assert len(calls) == 1  # pas de retry sur une contrainte violée


def test_real_database_lock_then_reinsertion_succeeds(tmp_path: Path) -> None:
    """Vrai verrou SQLite : une 2e connexion tient le verrou d'écriture, puis le relâche."""
    db_path = tmp_path / "locked.db"
    with closing(db.connect(db_path)) as setup:
        db.init_schema(setup)

    txs = load_transactions(CSV_GOOD)
    results = compute_results(txs)
    sleeps: list[float] = []

    with closing(sqlite3.connect(db_path, isolation_level=None)) as blocker:
        blocker.execute("BEGIN IMMEDIATE")  # prend le verrou d'écriture et ne le lâche pas

        def release_lock(delay: float) -> None:
            sleeps.append(delay)
            blocker.execute("COMMIT")  # l'autre programme a fini : le verrou disparaît pendant l'attente

        with closing(db.connect(db_path, timeout=0.0)) as writer:  # timeout 0 : échoue tout de suite
            inserted = retry(
                lambda: db.insert_file(
                    writer, name="x.csv", sha256="abc", transactions=txs, results=results
                ),
                attempts=3,
                sleep=release_lock,
            )

    assert inserted is True
    assert len(sleeps) == 1  # 1er essai bloqué, attente, 2e essai réussi
    assert count_transactions(db_path) == 3