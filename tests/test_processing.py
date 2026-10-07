import copy
from datetime import datetime
from decimal import Decimal

from txpipe.models import Transaction
from txpipe.processing import (
    flag_over_threshold,
    received_by_iban,
    sent_by_bank,
    sent_by_iban,
)


def make_tx(
    montant: str,
    iban_origine: str = "FR_A",
    banque: str = "BNP",
    iban_dest: str = "DE_X",
) -> Transaction:
    """Fabrique une transaction de test (aucun fichier lu)."""
    return Transaction(
        datetime_transaction=datetime(2024, 3, 1, 9, 0, 0),
        iban_origine=iban_origine,
        pays_source="FR",
        banque_source=banque,
        iban_destinataire=iban_dest,
        pays_destinataire="DE",
        montant=Decimal(montant),
        devise="EUR",
    )


def test_sent_by_iban() -> None:
    txs = [
        make_tx("10.00", iban_origine="A"),
        make_tx("5.50", iban_origine="A"),
        make_tx("3.00", iban_origine="B"),
    ]
    assert sent_by_iban(txs) == {"A": Decimal("15.50"), "B": Decimal("3.00")}


def test_sent_by_bank() -> None:
    txs = [make_tx("10", banque="X"), make_tx("20", banque="Y"), make_tx("5", banque="X")]
    assert sent_by_bank(txs) == {"X": Decimal("15"), "Y": Decimal("20")}


def test_received_by_iban() -> None:
    txs = [
        make_tx("10", iban_dest="Z"),
        make_tx("7", iban_dest="Z"),
        make_tx("1", iban_dest="W"),
    ]
    assert received_by_iban(txs) == {"Z": Decimal("17"), "W": Decimal("1")}


def test_empty_input() -> None:
    assert sent_by_iban([]) == {}
    assert flag_over_threshold([]) == []


def test_decimal_sums_are_exact() -> None:
    txs = [make_tx("0.10"), make_tx("0.20")]
    assert sent_by_iban(txs)["FR_A"] == Decimal("0.30")


def test_threshold_is_strict() -> None:
    txs = [make_tx("4999.99"), make_tx("5000.00"), make_tx("5000.01")]
    assert flag_over_threshold(txs) == [False, False, True]


def test_input_is_not_modified() -> None:
    txs = [make_tx("10", iban_origine="A"), make_tx("9000", iban_origine="B")]
    avant = copy.deepcopy(txs)
    sent_by_iban(txs)
    flag_over_threshold(txs)
    assert txs == avant  

def test_total_sent_equals_total_received() -> None:
    txs = [make_tx("100", iban_origine="A", iban_dest="X"), make_tx("50", iban_origine="B", iban_dest="Y")]
    assert sum(sent_by_iban(txs).values()) == sum(received_by_iban(txs).values())