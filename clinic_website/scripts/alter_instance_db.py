import sqlite3
p = r'e:/bhojani_website/clinic_website/instance/clinic_full.db'
print('DB exists=', __import__('os').path.exists(p))
conn = sqlite3.connect(p)
try:
    print('Before:', list(conn.execute("PRAGMA table_info('testimonial')")))
    try:
        conn.execute("ALTER TABLE testimonial ADD COLUMN featured BOOLEAN DEFAULT 0")
        conn.commit()
        print('ALTER applied')
    except Exception as e:
        print('ALTER failed:', e)
    print('After:', list(conn.execute("PRAGMA table_info('testimonial')")))
finally:
    conn.close()
