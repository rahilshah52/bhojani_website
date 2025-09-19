"""A minimal test runner that doesn't require pytest. Run with:
python run_tests_simple.py
"""
import io
from clinic_app import app, db, Staff, Patient, generate_password_hash

with app.app_context():
    db.drop_all()
    db.create_all()
    staff = Staff(name='T', email='staff@example.com', password_hash=generate_password_hash('pw'), role='staff')
    patient = Patient(name='P', email='p@example.com')
    db.session.add_all([staff, patient])
    db.session.commit()

client = app.test_client()

# staff login
rv = client.post('/staff/login', data={'email':'staff@example.com','password':'pw'}, follow_redirects=True)
print('staff login status:', rv.status_code)
print(rv.data.decode()[:200])

# upload
data = {'file': (io.BytesIO(b'Hello test'), 'report.txt')}
rv = client.post('/admin/upload/1', data=data, content_type='multipart/form-data', follow_redirects=True)
print('upload status:', rv.status_code)
print(rv.data.decode()[:200])

# impersonate
rv = client.get('/staff/impersonate/1', follow_redirects=True)
print('impersonate status:', rv.status_code)
print(rv.data.decode()[:200])

# list files
rv = client.get('/patient/files')
print('files page status:', rv.status_code)
print(rv.data.decode()[:400])

# find file id and download
from clinic_app import PatientFile
with app.app_context():
    pf = PatientFile.query.filter_by(patient_id=1).first()
    print('found patient file:', pf and pf.original_name)
    fid = pf.id
rv = client.get(f'/patient/files/{fid}/download')
print('download status:', rv.status_code)
print('download bytes start:', rv.data[:20])
