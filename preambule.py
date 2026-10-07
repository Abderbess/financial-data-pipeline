import sqlite3
from contextlib import closing

conn = sqlite3.connect("essai.db")
print("connexion ouverte :", conn)
conn.close()
print("connexion fermée")

with sqlite3.connect("essai.db") as conn:
    conn.execute("SELECT 1")
print("sorti du with")
conn.execute("SELECT 1")
print("la connexion était encore ouverte !")
conn.close()

with closing(sqlite3.connect("essai.db")) as conn:
    conn.execute("SELECT 1")
print("sorti du closing")
try:
    conn.execute("SELECT 1")
except sqlite3.ProgrammingError as e:
    print("connexion bien fermée :", e)

with closing(sqlite3.connect(":memory:")) as mem:
    mem.execute("CREATE TABLE t (x INTEGER)")
    mem.execute("INSERT INTO t VALUES (1)")
    print("en mémoire :", mem.execute("SELECT COUNT(*) FROM t").fetchone())

