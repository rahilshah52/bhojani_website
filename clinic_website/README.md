Clinic single-file Flask app

This is a single-file demo clinic web app (`clinic_app.py`) using Flask and SQLite. It includes basic patient signup/login, appointment requests, vitals logging, blog posts, FAQs, and a simple admin area.

Quick start (PowerShell on Windows):

1. Change to the project folder:

   ```powershell
   cd E:\bhojani_website\clinic_website
   ```

2. Create and activate a virtualenv:

   ```powershell
   python -m venv venv
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
   .\venv\Scripts\Activate.ps1
   ```

3. Install requirements:

   ```powershell
   pip install -r requirements.txt
   ```

4. (Optional) set env vars for secret and admin password:

   ```powershell
   $env:FH_SECRET = "replace-with-secret"
   $env:ADMIN_PASS = "admin123"
   ```

5. Run the app:

   ```powershell
   python .\clinic_app.py
   ```

6. Open http://127.0.0.1:5000 in your browser.

Notes:
- The app creates a SQLite file `clinic_full.db` on first run.
- This is a demo single-file app. For production, split templates and static assets into appropriate folders, enable HTTPS, and use a production WSGI server.
- SMTP and other integrations are placeholders and need configuration to work.
