# Check-in App

Flask-based check-in application for event attendees, with Google Sheets integration and a terminal companion.

## Setup
Install Python 3.11+, then run `pip install -r requirements.txt`. Configure `GOOGLE_SHEET_ID`, `CHECKIN_USERNAME` and `CHECKIN_PASSWORD` as environment variables. Google OAuth uses the `GOOGLE_CREDENTIALS` and `GOOGLE_TOKEN` variables or local `credentials.json` and `authorized_user.json` (ignored by Git).

Run `python app.py` for the web interface or `python checkin.py` for the CLI.

## Features
Select event unit and calling, look up attendees, record check-ins, and correct names/callings in authorized spreadsheets.

## Security
This review branch requires HTTP Basic credentials for **all** web routes and rejects requests when credentials are not configured. Basic authentication must be used over HTTPS; use a trusted identity-aware gateway and strong passwords for internet-facing deployments. There is no per-user audit trail or role model yet. Protect participant data, tokens and sheet exports; validate CSRF, row concurrency and Google OAuth scopes.

## Validation
Add isolated tests with a fake spreadsheet for authorized/unauthorized access, duplicate check-ins and invalid rows. Do not deploy or merge without validating real UI behavior and TLS configuration.
