from decimal import Decimal

import pytest

from txpipe.loader import CSV_COLUMNS, InvalidFileError, load_transactions

HEADER = ",".join(CSV_COLUMNS)
BONNE = "2024-03-01T09:12:00,FR_A,FR,BNP,DE_X,DE,1250.00,EUR"


def make_csv(*rows: str) -> str:
    """Construit le texte d'un CSV (en-tête + lignes). Aucun fichier."""
    return "\n".join([HEADER, *rows]) + "\n"


def test_valid_file_is_loaded() -> None:
    txs = load_transactions(make_csv(BONNE))
    assert len(txs) == 1
    assert txs[0]["montant"] == Decimal("1250.00")


def test_non_numeric_amount_rejects_whole_file() -> None:
    mauvaise = "2024-03-01T10:00:00,FR_A,FR,BNP,DE_X,DE,abc,EUR"
    with pytest.raises(InvalidFileError) as info:
        load_transactions(make_csv(BONNE, mauvaise))
    assert "ligne 3" in str(info.value)
    assert "montant" in str(info.value)


def test_unreadable_date_is_rejected() -> None:
    mauvaise = "pas-une-date,FR_A,FR,BNP,DE_X,DE,10.00,EUR"
    with pytest.raises(InvalidFileError, match="date illisible"):
        load_transactions(make_csv(mauvaise))


def test_missing_column_in_row_is_rejected() -> None:
    mauvaise = "2024-03-01T10:00:00,FR_A,FR,BNP,DE_X,DE,10.00"
    with pytest.raises(InvalidFileError, match="colonnes"):
        load_transactions(make_csv(mauvaise))


def test_missing_column_in_header_is_rejected() -> None:
    sans_devise = HEADER.replace(",devise", "")
    with pytest.raises(InvalidFileError, match="devise"):
        load_transactions(sans_devise + "\n")


@pytest.mark.parametrize("valeur", ["NaN", "Infinity", "-5.00", "0"])
def test_impossible_amounts_are_rejected(valeur: str) -> None:
    mauvaise = f"2024-03-01T10:00:00,FR_A,FR,BNP,DE_X,DE,{valeur},EUR"
    with pytest.raises(InvalidFileError):
        load_transactions(make_csv(mauvaise))