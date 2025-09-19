import sqlite3, os
p = os.path.normpath(os.path.join(os.path.dirname(__file__), 'instance', 'clinic_full.db'))
print('DB path:', p, 'exists=', os.path.exists(p))
if not os.path.exists(p):
    print('Instance DB not found; aborting')
else:
    conn = sqlite3.connect(p)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info('testimonial')")] or []
        print('testimonial cols before:', cols)
        if 'featured' not in cols:
            try:
                conn.execute("ALTER TABLE testimonial ADD COLUMN featured BOOLEAN DEFAULT 0")
                conn.commit()
                print('Added featured column to instance DB')
            except Exception as e:
                print('ALTER failed:', e)
        else:
            print('featured already present')
        cols_after = [r[1] for r in conn.execute("PRAGMA table_info('testimonial')")] or []
        print('testimonial cols after:', cols_after)
    finally:
        conn.close()
