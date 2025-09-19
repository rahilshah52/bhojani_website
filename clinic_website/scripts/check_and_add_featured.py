import sqlite3, os
p = os.path.join(os.path.dirname(__file__), '..', 'clinic_full.db')
p = os.path.normpath(p)
print('db=', p, 'exists=', os.path.exists(p))
if not os.path.exists(p):
    print('DB file not found; nothing to check')
else:
    conn = sqlite3.connect(p)
    try:
        cols = list(conn.execute("PRAGMA table_info('testimonial')"))
        print('cols:', cols)
        names = [r[1] for r in cols]
        print('col_names:', names)
        if 'featured' not in names:
            try:
                conn.execute("ALTER TABLE testimonial ADD COLUMN featured BOOLEAN DEFAULT 0")
                conn.commit()
                print('Added column featured')
            except Exception as e:
                print('Could not add column:', e)
        else:
            print('featured exists')
    finally:
        conn.close()
