"""Seed richer demo data into clinic_full.db for testing and visual QA.

This script is idempotent: it checks for existing slugs/text before inserting so
you can re-run it without duplicating entries.
"""
import os
import sqlite3
from datetime import datetime, timedelta

# Ensure the 'featured' column exists in the SQLite table before importing the ORM
# so SQLAlchemy doesn't attempt to SELECT a missing column.
DB_PATH = os.path.join(os.path.dirname(__file__), 'clinic_full.db')
try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('testimonial')")
    cols = [r[1] for r in cur.fetchall()]
    if 'featured' not in cols:
        try:
            cur.execute("ALTER TABLE testimonial ADD COLUMN featured BOOLEAN DEFAULT 0")
            conn.commit()
        except Exception:
            # If table doesn't exist yet or ALTER fails, ignore and let ORM create tables later
            pass
    cur.close()
    conn.close()
except Exception:
    # If sqlite file doesn't exist yet, we'll let clinic_app create tables and the ORM handle it
    pass

import clinic_app as clinic_mod
from clinic_app import app, db, Patient, FAQ, Testimonial, BlogPost, Appointment, Vitals
from clinic_app import Staff, generate_password_hash


def ensure_patient(name, email, phone):
    p = Patient.query.filter_by(email=email).first()
    if p:
        return p
    p = Patient(name=name, email=email, phone=phone)
    db.session.add(p)
    db.session.commit()
    return p


def add_if_missing(model, **kwargs):
    # generic helper: for BlogPost use slug, for Testimonial use author+text, for FAQ use q
    if model is BlogPost:
        if BlogPost.query.filter_by(slug=kwargs.get('slug')).first():
            return None
    if model is Testimonial:
        if Testimonial.query.filter_by(text=kwargs.get('text')).first():
            return None
    if model is FAQ:
        if FAQ.query.filter_by(q=kwargs.get('q')).first():
            return None
    obj = model(**kwargs)
    db.session.add(obj)
    return obj


def seed():
    with app.app_context():
        # Ensure tables exist and match current models (this will create testimonial table if missing)
        db.create_all()
        # Use sqlite3 directly to ALTER the table if 'featured' is missing (avoids SQLAlchemy caching issues)
        try:
            import sqlite3, os
            db_path = os.path.join(os.path.dirname(clinic_mod.__file__), 'clinic_full.db')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                try:
                    cols = [r[1] for r in conn.execute("PRAGMA table_info('testimonial')")] or []
                    if 'featured' not in cols:
                        try:
                            conn.execute("ALTER TABLE testimonial ADD COLUMN featured BOOLEAN DEFAULT 0")
                            conn.commit()
                            print('Added featured column via sqlite3')
                        except Exception as e:
                            print('Could not ALTER testimonial:', e)
                finally:
                    conn.close()
        except Exception:
            pass
        # Patients
        p1 = ensure_patient('Test Patient', 'test@example.com', '555-0100')
        p2 = ensure_patient('Alex Johnson', 'alex@example.com', '555-0101')
        p3 = ensure_patient('Maria Gomez', 'maria@example.com', '555-0102')

        # FAQs
        faqs = [
            ('What should I bring?', 'Bring your medication list, recent glucose logs, and ID.'),
            ('Do you offer telehealth?', 'Yes — we provide video consultations for follow-ups.'),
            ('How do I get my readings exported?', 'From your dashboard you can export vitals as CSV.'),
        ]
        for q, a in faqs:
            add_if_missing(FAQ, q=q, a=a)

        # Testimonials
        tlist = [
            ('Jane Doe', 'Excellent care and friendly staff. My blood sugar is finally stable.'),
            ('Ravi K.', 'The remote monitoring helped me avoid a hospital visit.'),
            ('Lina P.', 'Very knowledgeable team — they adjusted my meds and educated me.'),
            ('Mohammad S.', 'Convenient telehealth and clear plans for diet and exercise.'),
            ('Angela M.', 'Compassionate clinicians who listen and explain everything.'),
            ('Carlos V.', 'A team approach that really worked for my BP.'),
        ]
        for author, text in tlist:
            t = add_if_missing(Testimonial, author=author, text=text)
            # Mark a couple as featured for the homepage
            if t and author in ('Jane Doe', 'Ravi K.'):
                t.featured = True

        # Blog posts
        posts = [
            ('Managing Blood Sugar', 'managing-blood-sugar', 'Practical tips to keep your glucose in range.'),
            ('Home Blood Pressure Monitoring', 'home-bp', 'How to measure BP at home and what to record.'),
            ('Healthy Eating for Diabetes', 'healthy-eating', 'Simple nutrition tips for better glucose control.'),
            ('Understanding Your Meds', 'understanding-meds', 'Why medication reviews matter.'),
            ('Telehealth Visits: What to Expect', 'telehealth-expect', 'Prepare for a successful video visit.'),
        ]
        for title, slug, content in posts:
            add_if_missing(BlogPost, title=title, slug=slug, content=content)

        # Appointments
        # Add a few example appointments if missing
        if not Appointment.query.first():
            ap1 = Appointment(patient_id=p2.id, date=datetime.utcnow() + timedelta(days=3), reason='Follow-up', status='requested')
            ap2 = Appointment(patient_id=p3.id, date=datetime.utcnow() + timedelta(days=7), reason='Medication review', status='confirmed')
            db.session.add_all([ap1, ap2])

        # Vitals (for dashboard charts)
        if not Vitals.query.filter_by(patient_id=p1.id).first():
            base = datetime.utcnow() - timedelta(days=30)
            for i in range(10):
                v = Vitals(patient_id=p1.id, systolic=120 + (i % 6), diastolic=78 + (i % 5), glucose=100 + (i * 2.5), measured_at=base + timedelta(days=i*3))
                db.session.add(v)
        # Try to ensure the 'featured' column exists in older DBs. This is safe in SQLite
        # and will be ignored if the column already exists. We execute raw SQL at runtime.
        try:
            with db.engine.connect() as conn:
                conn.execute("ALTER TABLE testimonial ADD COLUMN featured BOOLEAN DEFAULT 0")
        except Exception:
            # If ALTER fails (column exists or DB locked), ignore — our model covers it.
            pass
        db.session.commit()
        # Create default staff/admin accounts (idempotent)
        staff_accounts = [
            ('Clinic Admin', 'admin@clinic.local', 'adminpass', 'admin'),
            ('Alice Nurse', 'alice.nurse@clinic.local', 'Alice123!', 'staff'),
            ('Bob Nurse', 'bob.nurse@clinic.local', 'Bob123!', 'staff'),
            ('Cara Nurse', 'cara.nurse@clinic.local', 'Cara123!', 'staff'),
            ('Dr. Lee', 'dr.lee@clinic.local', 'LeeDoc123!', 'doctor'),
            ('Sam Reception', 'sam.recep@clinic.local', 'Sam123!', 'staff'),
            ('Nina Coordinator', 'nina.coord@clinic.local', 'Nina123!', 'staff'),
            ('Omar Admin', 'omar.admin@clinic.local', 'Omar123!', 'staff'),
            ('Priya Nurse', 'priya.nurse@clinic.local', 'Priya123!', 'staff'),
            ('Carlos Nurse', 'carlos.nurse@clinic.local', 'Carlos123!', 'staff'),
        ]
        created = []
        for name, email, pw, role in staff_accounts:
            if not Staff.query.filter_by(email=email).first():
                s = Staff(name=name, email=email, password_hash=generate_password_hash(pw), role=role)
                db.session.add(s)
                created.append((email, pw))
        if created:
            db.session.commit()
            for e, p in created:
                print(f'Created staff account: {e} (password: {p})')
        else:
            print('Staff accounts already exist or were present')
        print('Seeded demo data (idempotent)')


if __name__ == '__main__':
    seed()
