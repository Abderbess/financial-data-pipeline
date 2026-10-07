import argparse
import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from txpipe import db
from txpipe.generate import generate_csv_files
from txpipe.loader import InvalidFileError, file_sha256, load_transactions
from txpipe.processing import compute_results

Status = Literal["inserted", "skipped", "failed"]


@dataclass(frozen=True)
class FileReport:
    name: str
    status: Status
    detail: str


def process_file(path: Path, conn: sqlite3.Connection) -> FileReport:
    """Traite UN fichier. Les erreurs attendues finissent dans le rapport, elles ne plantent pas tout."""
    try:
        raw = path.read_bytes()
        sha = file_sha256(raw)
        transactions = load_transactions(raw.decode("utf-8"))
        results = compute_results(transactions)
        inserted = db.insert_file(
            conn, name=path.name, sha256=sha, transactions=transactions, results=results
        )
    except InvalidFileError as exc:
        return FileReport(path.name, "failed", "fichier invalide: " + " | ".join(exc.errors))
    except UnicodeDecodeError as exc:
        return FileReport(path.name, "failed", f"encodage illisible: {exc}")
    except (OSError, sqlite3.Error) as exc:
        return FileReport(path.name, "failed", f"{type(exc).__name__}: {exc}")

    if not inserted:
        return FileReport(path.name, "skipped", f"déjà traité (sha256={sha[:12]}...)")
    return FileReport(path.name, "inserted", f"{len(transactions)} transactions insérées")


def run(
    data_dir: Path,
    db_path: Path,
    *,
    generate: bool = True,
    n_files: int = 3,
    seed: int = 42,
    out: Callable[[str], None] = print,
) -> int:
    """Lance toute la pipeline. Retourne le code de retour (0 = OK, 1 = échec, 2 = rien à faire)."""
    if generate:
        paths = generate_csv_files(data_dir, n_files=n_files, seed=seed)
        out(f"[generate] {len(paths)} fichiers écrits dans {data_dir}")

    files = sorted(data_dir.glob("*.csv"))
    if not files:
        out(f"[erreur] aucun fichier CSV dans {data_dir}")
        return 2

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(db_path)
    try:
        db.init_schema(conn)
        reports = [process_file(p, conn) for p in files]
    finally:
        conn.close()

    labels: dict[Status, str] = {"inserted": "OK  ", "skipped": "SKIP", "failed": "FAIL"}
    for report in reports:
        out(f"[{labels[report.status]}] {report.name} : {report.detail}")

    nb_ok = sum(1 for r in reports if r.status == "inserted")
    nb_skip = sum(1 for r in reports if r.status == "skipped")
    nb_fail = sum(1 for r in reports if r.status == "failed")
    code = 1 if nb_fail else 0
    out(f"Résumé : {nb_ok} inséré(s), {nb_skip} ignoré(s), {nb_fail} en échec -> code de retour {code}")
    return code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="txpipe", description="Pipeline de transactions CSV -> SQLite")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--db", type=Path, default=Path("pipeline.db"))
    parser.add_argument("--skip-generate", action="store_true", help="ne pas générer de CSV")
    parser.add_argument("--files", type=int, default=3, help="nombre de CSV à générer")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    return run(
        args.data_dir,
        args.db,
        generate=not args.skip_generate,
        n_files=args.files,
        seed=args.seed,
    )