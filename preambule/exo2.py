import sqlite3
from contextlib import closing

with closing(sqlite3.connect("essai.db")) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, pays TEXT)")
    print("1ère création OK")
    conn.execute("CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, pays TEXT)")
    print("2ème création OK")