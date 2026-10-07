import csv
import io
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation

from txpipe.models import Transaction

CSV_COLUMNS = (
    "datetime_transaction", "iban_origine", "pays_source", "banque_source",
    "iban_destinataire", "pays_destinataire", "montant", "devise",
)


class InvalidRowError(ValueError):
    """Une ligne du CSV est invalide."""


class InvalidFileError(Exception):
    """Le fichier est rejeté. `errors` liste tous les problèmes trouvés."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def parse_row(fields: Mapping[str, str], line: int) -> Transaction:
    try:
        moment = datetime.fromisoformat(fields["datetime_transaction"])
    except ValueError:
        raise InvalidRowError(f"ligne {line}: date illisible") from None

    try:
        montant = Decimal(fields["montant"])
    except InvalidOperation:
        raise InvalidRowError(f"ligne {line}: montant non numérique: {fields['montant']!r}") from None

    if not montant.is_finite():
        raise InvalidRowError(f"ligne {line}: montant non fini: {fields['montant']!r}")
    if montant <= 0:
        raise InvalidRowError(f"ligne {line}: montant doit être > 0: {fields['montant']!r}")

    return Transaction(
        datetime_transaction=moment,
        iban_origine=fields["iban_origine"],
        pays_source=fields["pays_source"],
        banque_source=fields["banque_source"],
        iban_destinataire=fields["iban_destinataire"],
        pays_destinataire=fields["pays_destinataire"],
        montant=montant,
        devise=fields["devise"],
    )


def load_transactions(content: str) -> list[Transaction]:
    reader = csv.reader(io.StringIO(content))
    try:
        header = next(reader)
    except StopIteration:
        raise InvalidFileError(["fichier vide"]) from None

    missing = [c for c in CSV_COLUMNS if c not in header]
    if missing:
        raise InvalidFileError([f"colonnes manquantes dans l'en-tête: {missing}"])

    transactions: list[Transaction] = []
    errors: list[str] = []
    for row in reader:
        if not row:
            continue
        line = reader.line_num
        if len(row) != len(header):
            errors.append(f"ligne {line}: {len(row)} colonnes au lieu de {len(header)}")
            continue
        try:
            transactions.append(parse_row(dict(zip(header, row)), line))
        except InvalidRowError as exc:
            errors.append(str(exc))

    if errors:
        raise InvalidFileError(errors)
    return transactions