from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypedDict


class Transaction(TypedDict):
    datetime_transaction: datetime
    iban_origine: str
    pays_source: str
    banque_source: str
    iban_destinataire: str
    pays_destinataire: str
    montant: Decimal
    devise: str


@dataclass(frozen=True)
class ProcessingResults:
    """Tous les résultats du traitement d'un fichier."""

    sent_by_iban: dict[str, Decimal]
    sent_by_bank: dict[str, Decimal]
    received_by_iban: dict[str, Decimal]
    over_threshold: list[bool]  # un drapeau par transaction, dans le même ordre