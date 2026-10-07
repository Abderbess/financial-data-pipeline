from pathlib import Path

from txpipe.loader import load_transactions
from txpipe.processing import flag_over_threshold, received_by_iban, sent_by_bank, sent_by_iban

txs = load_transactions(Path("data/transactions_01.csv").read_text(encoding="utf-8"))

print("envoyé par iban  :", sent_by_iban(txs))
print("envoyé par banque:", sent_by_bank(txs))
print("reçu par iban    :", received_by_iban(txs))
print("drapeaux > 5000  :", flag_over_threshold(txs))