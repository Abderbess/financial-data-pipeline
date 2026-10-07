from pathlib import Path

from txpipe import db
from txpipe.loader import load_transactions
from txpipe.processing import compute_results

contenu = Path("data/transactions_01.csv").read_text(encoding="utf-8")
txs = load_transactions(contenu)
results = compute_results(txs)

conn = db.connect(":memory:")
db.init_schema(conn)

print("1er appel :", db.insert_file(conn, name="transactions_01.csv", sha256="abc", transactions=txs, results=results))
print("2e appel  :", db.insert_file(conn, name="transactions_01.csv", sha256="abc", transactions=txs, results=results))
print("fichiers     :", conn.execute("SELECT COUNT(*) FROM fichiers").fetchone()[0])
print("transactions :", conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
print("agrégats     :", conn.execute("SELECT COUNT(*) FROM agregats").fetchone()[0])
print("> 5000       :", conn.execute("SELECT COUNT(*) FROM transactions WHERE depasse_seuil = 1").fetchone()[0])
conn.close()