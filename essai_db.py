from txpipe import db

conn = db.connect(":memory:")
db.init_schema(conn)
tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print(tables)
print("clés étrangères actives :", conn.execute("PRAGMA foreign_keys").fetchone()[0])
conn.close()