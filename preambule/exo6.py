import sqlite3
from contextlib import closing

with closing(sqlite3.connect("exo6.db")) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, pays TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS commandes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "client_id INTEGER REFERENCES clients(id), "
        "montant INTEGER)"
    )
    conn.commit()

    conn.execute("INSERT INTO commandes (client_id, montant) VALUES (?, ?)", (999, 100))
    print("sans PRAGMA : insertion passée, client 999 n'existe pas !")
    conn.rollback()  

    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("INSERT INTO commandes (client_id, montant) VALUES (?, ?)", (999, 100))
        print("avec PRAGMA : insertion passée (mauvais signe)")
    except sqlite3.IntegrityError as e:
        print("avec PRAGMA : insertion refusée ->", e)