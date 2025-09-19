import sqlite3, os
base = os.path.join(os.path.dirname(__file__), '..')
paths = [os.path.join(base, 'clinic_full.db'), os.path.join(base, 'instance', 'clinic_full.db')]
for p in paths:
    p = os.path.normpath(p)
    print('\nDB:', p, 'exists=', os.path.exists(p))
    if not os.path.exists(p):
        continue
    conn = sqlite3.connect(p)
    try:
        tables = list(conn.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        print('tables:', tables)
        for t in ['testimonial']:
            cols = list(conn.execute(f"PRAGMA table_info('{t}')"))
            print(f"{t} cols:", cols)
    finally:
        conn.close()
