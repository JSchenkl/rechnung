# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Flask-basierte Rechnungs-Web-App für Julius Schenkl (Haushaltshilfe-Dienstleistungen, Kleinunternehmer § 19 UStG). Rechnungen werden als PDF generiert und automatisch per E-Mail versendet.

## Setup (einmalig)

```powershell
# MySQL-Datenbank anlegen
mysql -u root -e "CREATE DATABASE rechnung CHARACTER SET utf8mb4; CREATE USER 'rechnung'@'localhost' IDENTIFIED BY 'password'; GRANT ALL ON rechnung.* TO 'rechnung'@'localhost';"

# Virtuelle Umgebung + Pakete
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# .env anlegen (aus .env.example kopieren, Werte eintragen)
copy .env.example .env

# Datenbank-Migrationen
flask db init
flask db migrate -m "initial"
flask db upgrade
```

## Entwicklungsserver starten

```powershell
venv\Scripts\activate
flask run
# → http://127.0.0.1:5000
```

## Migrationen (nach Modelländerungen)

```powershell
flask db migrate -m "beschreibung"
flask db upgrade
```

## Architektur

```
app/
├── __init__.py        # App-Factory: Flask, SQLAlchemy, Flask-Login, CSRF
├── models.py          # Customer, Service, Invoice, InvoiceItem
├── auth.py            # Single-User-Login (Passwort aus .env → ADMIN_PASSWORD)
├── email_utils.py     # generate_pdf() via WeasyPrint, send_invoice_email() via smtplib
└── routes/
    ├── main.py        # Dashboard /
    ├── customers.py   # /customers CRUD
    ├── services.py    # /services CRUD (Leistungskatalog)
    └── invoices.py    # /invoices – Liste, Erstellen, Detail, PDF, E-Mail, Bezahlt
```

### Datenfluss Rechnungsversand
1. `invoices.send` → `email_utils.send_invoice_email(invoice)`
2. `generate_pdf()` rendert `invoices/pdf.html` → WeasyPrint → bytes
3. `smtplib.SMTP` versendet E-Mail mit PDF-Anhang an `invoice.customer.email`
4. Status wechselt auf `sent`, `Invoice.sent_at` wird gesetzt

### Rechnungsnummer-Format
`YYYY-NNN` (z.B. `2026-001`) – automatisch inkrementiert per Jahr in `invoices._next_invoice_number()`.

### PDF-Pflichtangaben (§ 19 UStG Kleinunternehmer)
Template `invoices/pdf.html` enthält alle deutschen Pflichtangaben. Eigene Daten (Name, Adresse, IBAN) kommen aus `.env` → `config.py` → `OWNER_*`.

## Deployment (IONOS VPS – später)

`.github/workflows/deploy.yml` ist vorbereitet aber deaktiviert (`if: false`). Aktivierung:
1. `if: false` entfernen
2. GitHub Secrets setzen: `VPS_HOST`, `VPS_USER`, `VPS_KEY`, `VPS_PATH`
3. Auf dem VPS: nginx + gunicorn + systemd-Service einrichten
