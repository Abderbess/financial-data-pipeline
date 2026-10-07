from collections.abc import Sequence
from decimal import Decimal

from txpipe.models import ProcessingResults, Transaction

SEUIL = Decimal("5000")


def sent_by_iban(transactions: Sequence[Transaction]) -> dict[str, Decimal]:
    """Somme des montants envoyés, par IBAN d'origine."""
    totals: dict[str, Decimal] = {}
    for tx in transactions:
        iban = tx["iban_origine"]
        totals[iban] = totals.get(iban, Decimal("0")) + tx["montant"]
    return totals


def sent_by_bank(transactions: Sequence[Transaction]) -> dict[str, Decimal]:
    """Somme des montants envoyés, par banque source."""
    totals: dict[str, Decimal] = {}
    for tx in transactions:
        banque = tx["banque_source"]
        totals[banque] = totals.get(banque, Decimal("0")) + tx["montant"]
    return totals


def received_by_iban(transactions: Sequence[Transaction]) -> dict[str, Decimal]:
    """Somme des montants reçus, par IBAN destinataire."""
    totals: dict[str, Decimal] = {}
    for tx in transactions:
        iban = tx["iban_destinataire"]
        totals[iban] = totals.get(iban, Decimal("0")) + tx["montant"]
    return totals


def flag_over_threshold(transactions: Sequence[Transaction]) -> list[bool]:
    """Un drapeau par transaction : True si le montant dépasse STRICTEMENT 5000."""
    return [tx["montant"] > SEUIL for tx in transactions]

def compute_results(transactions: Sequence[Transaction]) -> ProcessingResults:
    return ProcessingResults(
        sent_by_iban=sent_by_iban(transactions),
        sent_by_bank=sent_by_bank(transactions),
        received_by_iban=received_by_iban(transactions),
        over_threshold=flag_over_threshold(transactions),
    )