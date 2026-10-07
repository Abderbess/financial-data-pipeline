from contextlib import closing
from pathlib import Path

import pytest

from txpipe import db
from txpipe.loader import CSV_COLUMNS
from txpipe.pipeline import run

HEADER = ",".join(CSV_COLUMNS)

CSV_GOOD = f"""{HEADER}
2024-03-01T09:12:00,FR_A,FR,BNP,DE_X,DE,1250.00,EUR
2024-03-01T10:45:00,FR_A,FR,BNP,ES_Y,ES,7400.50,EUR
2024-03-01T11:00:00,GB_B,GB,NATWEST,DE_X,DE,100.10,EUR
"""

# La 1re ligne est valide, la 2e a un montant non numérique
CSV_BAD_AMOUNT = f"""{HEADER}
2024-03-03T09:00:00,FR_A,FR,BNP,DE_X,DE,100.00,EUR
2024-03-03T10:00:00,FR_A,FR,BNP,ES_Y,ES,abc,EUR
"""


def count(db_path: Path, table: str) -> int:
    with closing(db.connect(db_path)) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_invalid_amount_gives_nonzero_code_and_clean_db(tmp_path: Path) -> None:
    data, db_path = tmp_path / "data", tmp_path / "p.db"
    data.mkdir()
    (data / "bad.csv").write_text(CSV_BAD_AMOUNT, encoding="utf-8")
    lines: list[str] = []

    code = run(data, db_path, generate=False, out=lines.append)

    assert code != 0
    assert any("FAIL" in line and "bad.csv" in line for line in lines)
    # La 1re ligne (valide) du fichier ne doit PAS être en base : pas d'insertion partielle
    assert count(db_path, "fichiers") == 0
    assert count(db_path, "transactions") == 0
    assert count(db_path, "agregats") == 0


def test_bad_file_does_not_corrupt_the_good_ones(tmp_path: Path) -> None:
    data, db_path = tmp_path / "data", tmp_path / "p.db"
    data.mkdir()
    (data / "good.csv").write_text(CSV_GOOD, encoding="utf-8")
    (data / "bad.csv").write_text(CSV_BAD_AMOUNT, encoding="utf-8")

    code = run(data, db_path, generate=False, out=lambda _l: None)

    assert code != 0  # un fichier a échoué : la pipeline le signale
    assert count(db_path, "fichiers") == 1  # seul good.csv est là
    assert count(db_path, "transactions") == 3


def test_missing_column_in_header_fails(tmp_path: Path) -> None:
    data, db_path = tmp_path / "data", tmp_path / "p.db"
    data.mkdir()
    sans_devise = HEADER.replace(",devise", "") + "\n2024-03-01T09:00:00,A,FR,B,C,DE,10.00\n"
    (data / "x.csv").write_text(sans_devise, encoding="utf-8")

    assert run(data, db_path, generate=False, out=lambda _l: None) != 0
    assert count(db_path, "fichiers") == 0


def test_failure_in_the_middle_of_insertion_is_rolled_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fichier valide, mais l'écriture des agrégats plante APRÈS celle des transactions."""
    data, db_path = tmp_path / "data", tmp_path / "p.db"
    data.mkdir()
    (data / "good.csv").write_text(CSV_GOOD, encoding="utf-8")

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("panne simulée pendant l'insertion des agrégats")

    monkeypatch.setattr(db, "_insert_aggregates", boom)
    with pytest.raises(RuntimeError):
        run(data, db_path, generate=False, out=lambda _l: None)

    # Les 3 transactions déjà écrites ont été annulées par le ROLLBACK
    assert count(db_path, "fichiers") == 0
    assert count(db_path, "transactions") == 0

    # Le bug est "corrigé" : une relance traite normalement le fichier
    monkeypatch.undo()
    assert run(data, db_path, generate=False, out=lambda _l: None) == 0
    assert count(db_path, "transactions") == 3