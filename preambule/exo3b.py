import sqlite3
from contextlib import closing

with closing(sqlite3.connect("essai.db")) as conn:
    conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", ("Fantôme", "FR"))
    # PAS de commit ici
    n = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    print("vu par la même connexion :", n, "clients")

with closing(sqlite3.connect("essai.db")) as conn:
    n = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    print("après fermeture et réouverture :", n, "clients")