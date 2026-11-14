import sqlite3

conn = sqlite3.connect("backend/crowdwise.db")
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables and counts in backend/crowdwise.db:")
for t in sorted(tables):
    try:
        cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  - {t:<22}: {cnt:>8} rows")
    except Exception as e:
        print(f"  - {t:<22}: error ({e})")
conn.close()
