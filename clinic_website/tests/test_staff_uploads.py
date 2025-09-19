import os
import io
import pytest
from clinic_app import app, db, Staff, Patient, generate_password_hash

@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # create a staff user and a patient
            staff = Staff(name='T', email='staff@example.com', password_hash=generate_password_hash('pw'), role='staff')
            patient = Patient(name='P', email='p@example.com')
            db.session.add_all([staff, patient])
            db.session.commit()
        yield client


def test_staff_login_and_upload_and_download(client, tmp_path):
    # staff login
    rv = client.post('/staff/login', data={'email':'staff@example.com','password':'pw'}, follow_redirects=True)
    assert b'Staff logged in' in rv.data
    # upload a small text file for patient id 1
    data = {
        'file': (io.BytesIO(b'Hello test'), 'report.txt')
    }
    rv = client.post('/admin/upload/1', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'File uploaded' in rv.data
    # impersonate patient 1
    rv = client.get('/staff/impersonate/1', follow_redirects=True)
    assert b'Now impersonating' in rv.data
    # list patient files
    rv = client.get('/patient/files')
    assert b'report.txt' in rv.data
    # download file (find generated file id in DB)
    from clinic_app import PatientFile
    with app.app_context():
        pf = PatientFile.query.filter_by(patient_id=1).first()
        assert pf is not None
        fid = pf.id
    rv = client.get(f'/patient/files/{fid}/download')
    assert rv.status_code == 200
    assert rv.data.startswith(b'Hello test')
