import sqlite3
from contextlib import closing

malveillant = "Robert'); DROP TABLE clients;--"

with closing(sqlite3.connect("exo5.db")) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, pays TEXT)")

    conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", (malveillant, "FR"))
    conn.commit()

    nom = conn.execute("SELECT nom FROM clients").fetchone()[0]
    print("nom stocké :", nom)
    print("la table existe encore ?", conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0], "ligne(s)")