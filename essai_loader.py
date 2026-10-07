from pathlib import Path

from txpipe.loader import InvalidFileError, load_transactions

contenu = Path("data/transactions_01.csv").read_text(encoding="utf-8")
txs = load_transactions(contenu)
print(len(txs), "transactions chargées")

mauvais = contenu + "2024-03-09T09:00:00,A,FR,B,C,DE,abc,EUR\n"
try:
    load_transactions(mauvais)
except InvalidFileError as e:
    print("fichier rejeté :", e)