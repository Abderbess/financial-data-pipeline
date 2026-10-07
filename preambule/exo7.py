import sqlite3
from contextlib import closing

with closing(sqlite3.connect("exo7.db")) as conn:
    conn.execute("DROP TABLE IF EXISTS clients")
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, pays TEXT)")
    conn.commit()

    try:
        conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", ("Alice", "FR"))
        print("1ère insertion OK")
        conn.execute("INSERT INTO clients (nom, pays) VALUES (?, ?)", (None, "FR")) 
        print("2ème insertion OK")
        conn.commit()
    except sqlite3.IntegrityError as e:
        print("erreur :", e)
        conn.rollback()
        print("rollback fait")

    n = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    print("clients en base :", n)