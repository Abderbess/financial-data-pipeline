import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

HEADER = [
    "datetime_transaction", "iban_origine", "pays_source", "banque_source",
    "iban_destinataire", "pays_destinataire", "montant", "devise",
]

# (iban, pays, banque) : seulement 3 origines, donc des IBAN reviennent forcément
ORIGINS = [
    ("FR7630006000011234567890189", "FR", "BNPPARIBAS"),
    ("GB29NWBK60161331926819", "GB", "NATWEST"),
    ("BE68539007547034", "BE", "KBC"),
]
DESTINATIONS = [
    ("DE89370400440532013000", "DE"),
    ("ES9121000418450200051332", "ES"),
    ("IT60X0542811101000000123456", "IT"),
    ("NL91ABNA0417164300", "NL"),
]


def format_cents(cents: int) -> str:
    """12345 -> '123.45' (sans passer par un float)."""
    return f"{cents // 100}.{cents % 100:02d}"


def generate_rows(rng: random.Random, n_rows: int, start: datetime) -> list[list[str]]:
    rows: list[list[str]] = []
    moment = start
    for i in range(n_rows):
        moment += timedelta(minutes=rng.randint(15, 180))
        iban, pays, banque = rng.choice(ORIGINS)
        dest_iban, dest_pays = rng.choice(DESTINATIONS)
        if i < 2:
            cents = rng.randint(500_001, 900_000)  # les 2 premières lignes dépassent 5000
        else:
            cents = rng.randint(1_000, 600_000)
        rows.append([
            moment.isoformat(timespec="seconds"),
            iban, pays, banque, dest_iban, dest_pays,
            format_cents(cents),
            "EUR",
        ])
    return rows


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)


def generate_csv_files(directory: Path, *, n_files: int = 3, seed: int = 42) -> list[Path]:
    """Écrit n_files fichiers transactions_XX.csv, toujours identiques pour une même graine."""
    rng = random.Random(seed)  # graine fixe : mêmes fichiers à chaque lancement
    paths: list[Path] = []
    for index in range(1, n_files + 1):
        rows = generate_rows(rng, rng.randint(5, 10), datetime(2024, 3, index, 8, 0))
        path = directory / f"transactions_{index:02d}.csv"
        write_csv(path, rows)
        paths.append(path)
    return paths