"""Wrapper to run the clinic app with `python app.py`.
This imports `app` from `clinic_app.py` and starts it.
"""
from clinic_app import app

if __name__ == '__main__':
    # Use the same default as clinic_app.py (debug=True) for local development
    app.run(debug=True)
