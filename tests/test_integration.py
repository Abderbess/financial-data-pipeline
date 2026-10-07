import sqlite3
from contextlib import closing
from pathlib import Path

from txpipe import db
from txpipe.loader import CSV_COLUMNS
from txpipe.pipeline import run

HEADER = ",".join(CSV_COLUMNS)

# Fichier A : 3 lignes, une seule au-dessus de 5000 (7400.50)
CSV_A = f"""{HEADER}
2024-03-01T09:12:00,FR_A,FR,BNP,DE_X,DE,1250.00,EUR
2024-03-01T10:45:00,FR_A,FR,BNP,ES_Y,ES,7400.50,EUR
2024-03-01T11:00:00,GB_B,GB,NATWEST,DE_X,DE,100.10,EUR
"""

# Fichier B : 5000.00 (PAS au-dessus du seuil) et 5000.01 (au-dessus)
CSV_B = f"""{HEADER}
2024-03-02T09:00:00,FR_A,FR,BNP,DE_X,DE,5000.00,EUR
2024-03-02T10:00:00,GB_B,GB,NATWEST,ES_Y,ES,5000.01,EUR
"""


def quiet(_: str) -> None:
    """N'affiche rien : on ne veut pas polluer la sortie des tests."""


def run_pipeline(data_dir: Path, db_path: Path) -> int:
    return run(data_dir, db_path, generate=False, out=quiet)


def count(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def totals(conn: sqlite3.Connection, kind: str) -> dict[str, int]:
    """Totaux en centimes, tous fichiers confondus, pour un type d'agrégat."""
    rows = conn.execute(
        "SELECT cle, SUM(total_centimes) AS total FROM agregats WHERE type = ? GROUP BY cle",
        (kind,),
    ).fetchall()
    return {str(r["cle"]): int(r["total"]) for r in rows}


def make_data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.csv").write_text(CSV_A, encoding="utf-8")
    (data / "b.csv").write_text(CSV_B, encoding="utf-8")
    return data


def test_inserted_data_has_the_right_values(tmp_path: Path) -> None:
    data, db_path = make_data_dir(tmp_path), tmp_path / "p.db"

    assert run_pipeline(data, db_path) == 0

    with closing(db.connect(db_path)) as conn:
        # 1. Nombre de lignes : 3 (fichier A) + 2 (fichier B)
        assert count(conn, "SELECT COUNT(*) FROM fichiers") == 2
        assert count(conn, "SELECT COUNT(*) FROM transactions") == 5

        # 2. Totaux par IBAN, calculés à la main (en centimes)
        assert totals(conn, "envoye_par_iban") == {
            "FR_A": 1365050,  # 1250.00 + 7400.50 + 5000.00
            "GB_B": 510011,   # 100.10 + 5000.01
        }
        assert totals(conn, "recu_par_iban") == {
            "DE_X": 635010,   # 1250.00 + 100.10 + 5000.00
            "ES_Y": 1240051,  # 7400.50 + 5000.01
        }
        assert totals(conn, "envoye_par_banque") == {"BNP": 1365050, "NATWEST": 510011}

        # 3. Transactions au-dessus de 5000 : 7400.50 et 5000.01 (PAS 5000.00)
        assert count(conn, "SELECT COUNT(*) FROM transactions WHERE depasse_seuil = 1") == 2


def test_rerun_does_not_create_duplicates(tmp_path: Path) -> None:
    data, db_path = make_data_dir(tmp_path), tmp_path / "p.db"

    assert run_pipeline(data, db_path) == 0
    assert run_pipeline(data, db_path) == 0  # on relance...
    assert run_pipeline(data, db_path) == 0  # ...encore une fois

    with closing(db.connect(db_path)) as conn:
        assert count(conn, "SELECT COUNT(*) FROM fichiers") == 2
        assert count(conn, "SELECT COUNT(*) FROM transactions") == 5
        assert totals(conn, "envoye_par_iban")["FR_A"] == 1365050  # pas doublé


def test_same_content_under_another_name_is_not_processed_twice(tmp_path: Path) -> None:
    data, db_path = make_data_dir(tmp_path), tmp_path / "p.db"
    run_pipeline(data, db_path)

    (data / "copie_de_a.csv").write_text(CSV_A, encoding="utf-8")  # même contenu, autre nom
    assert run_pipeline(data, db_path) == 0

    with closing(db.connect(db_path)) as conn:
        assert count(conn, "SELECT COUNT(*) FROM fichiers") == 2
        assert count(conn, "SELECT COUNT(*) FROM transactions") == 5


def test_same_name_with_different_content_is_processed(tmp_path: Path) -> None:
    data, db_path = make_data_dir(tmp_path), tmp_path / "p.db"
    run_pipeline(data, db_path)

    (data / "a.csv").write_text(CSV_A.replace("1250.00", "1251.00"), encoding="utf-8")
    assert run_pipeline(data, db_path) == 0

    with closing(db.connect(db_path)) as conn:
        assert count(conn, "SELECT COUNT(*) FROM fichiers") == 3
        assert count(conn, "SELECT COUNT(*) FROM transactions") == 8  # 5 + 3


def test_full_pipeline_with_generation(tmp_path: Path) -> None:
    data, db_path = tmp_path / "data", tmp_path / "p.db"

    assert run(data, db_path, generate=True, out=quiet) == 0
    assert run(data, db_path, generate=True, out=quiet) == 0  # mêmes fichiers (graine fixe)

    with closing(db.connect(db_path)) as conn:
        assert count(conn, "SELECT COUNT(*) FROM fichiers") == 3
        assert count(conn, "SELECT COUNT(*) FROM transactions WHERE depasse_seuil = 1") >= 6