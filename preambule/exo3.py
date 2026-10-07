import sqlite3
from contextlib import closing

with closing(sqlite3.connect("essai.db")) as conn:
    conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", ("Alice", "FR"))
    conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", ("Bob", "DE"))
    conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", ("Chloé", "FR"))

    conn.executemany(
        "INSERT INTO clients (nom, pays) VALUES (?, ?)",
        [("Dan", "ES"), ("Eve", "FR"), ("Farid", "DE")],
    )

    conn.commit() 

with closing(sqlite3.connect("essai.db")) as conn:
    lignes = conn.execute("SELECT * FROM clients").fetchall()
    print("nombre de clients :", len(lignes))
    for ligne in lignes:
        print(ligne)