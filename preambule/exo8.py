import sqlite3
from contextlib import closing

with closing(sqlite3.connect("exo8.db")) as conn:
    conn.execute("DROP TABLE IF EXISTS clients")
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE)")
    conn.execute("INSERT INTO clients (email) VALUES (?)", ("a@x.fr",))
    conn.commit()

    try:
        conn.execute("INSERT INTO clients (email) VALUES (?)", ("a@x.fr",)) 
    except sqlite3.Error as e:
        print("type exact :", type(e))
        print("message    :", e)