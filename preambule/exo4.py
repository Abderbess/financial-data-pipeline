import sqlite3
from contextlib import closing

with closing(sqlite3.connect("essai.db")) as conn:
    conn.row_factory = sqlite3.Row
    resultat = conn.execute(
        "SELECT pays, COUNT(*) AS nb FROM clients GROUP BY pays ORDER BY pays"
    )
    for ligne in resultat:
        print("pays :", ligne["pays"], "| nombre :", ligne["nb"])