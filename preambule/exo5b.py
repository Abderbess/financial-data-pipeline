import sqlite3
from contextlib import closing

malveillant = "Robert'); DROP TABLE clients;--"

with closing(sqlite3.connect("exo5.db")) as conn:
    requete = f"INSERT INTO clients (nom) VALUES ('{malveillant}')"
    print("requête construite :", requete)

    try:
        conn.execute(requete)
    except sqlite3.Error as e:
        print("execute ->", type(e).__name__, ":", e)

    conn.executescript(requete)

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'"
    ).fetchall()
    print("la table clients existe encore ?", len(tables) > 0)