"""Top-level runner so `python app.py` from E:\bhojani_website works.
It imports the app from the clinic_website package folder.
"""
import sys
from os import path

# Ensure the clinic_website folder is on sys.path
PROJECT_ROOT = path.dirname(__file__)
APP_FOLDER = path.join(PROJECT_ROOT, 'clinic_website')
if APP_FOLDER not in sys.path:
    sys.path.insert(0, APP_FOLDER)

try:
    from clinic_app import app
except Exception as e:
    print('Failed to import clinic_app from clinic_website folder:', e)
    raise

if __name__ == '__main__':
    app.run(debug=True)
