import email as emaillib
import imaplib
import io
import random
import re
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import render_template, current_app
from xhtml2pdf import pisa


def _owner(app):
    return {
        'name': app.config['OWNER_NAME'],
        'street': app.config['OWNER_STREET'],
        'postal_code': app.config['OWNER_POSTAL_CODE'],
        'city': app.config['OWNER_CITY'],
        'iban': app.config['OWNER_IBAN'],
        'email': app.config['OWNER_EMAIL'],
    }


def generate_pdf(invoice):
    app = current_app._get_current_object()
    html = render_template('invoices/pdf.html', invoice=invoice, owner=_owner(app))
    buf = io.BytesIO()
    pisa.CreatePDF(html.encode('utf-8'), dest=buf, encoding='utf-8')
    return buf.getvalue()


def _send_smtp(msg, app):
    context = ssl.create_default_context()
    if app.config['MAIL_USE_TLS']:
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls(context=context)
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], context=context) as server:
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)


def send_invoice_email(invoice):
    app = current_app._get_current_object()
    owner = _owner(app)

    pdf_bytes = generate_pdf(invoice)
    filename = f"Rechnung_{invoice.invoice_number}.pdf"

    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = invoice.customer.email
    msg['Subject'] = f"Rechnung {invoice.invoice_number} von {owner['name']}"

    body = render_template('emails/invoice.txt', invoice=invoice, owner=owner)
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    attachment = MIMEApplication(pdf_bytes, Name=filename)
    attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(attachment)

    _send_smtp(msg, app)


def run_lottery_draw(invoice):
    """33 % Chance auf Gewinn. Sendet sofort eine Gewinn- oder Verlier-E-Mail."""
    from app.models import LotteryEntry
    from app import db

    app = current_app._get_current_object()
    won = random.random() < 1 / 3
    entry = LotteryEntry(
        invoice_id=invoice.id,
        won=won,
        code=LotteryEntry.generate_code() if won else None,
    )
    db.session.add(entry)
    db.session.commit()

    if won:
        _send_lottery_win_email(invoice, entry, app)
    else:
        _send_lottery_lose_email(invoice, app)


def _send_lottery_win_email(invoice, entry, app):
    owner = _owner(app)
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = invoice.customer.email
    msg['Subject'] = f"Sie haben gewonnen! Gewinnspiel zu Rechnung {invoice.invoice_number}"
    msg.attach(MIMEText(
        render_template('emails/lottery_win.txt', invoice=invoice, owner=owner, code=entry.code),
        'plain', 'utf-8',
    ))
    _send_smtp(msg, app)


def _send_lottery_lose_email(invoice, app):
    owner = _owner(app)
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = invoice.customer.email
    msg['Subject'] = f"Ihr Gewinnspiel-Ergebnis zu Rechnung {invoice.invoice_number}"
    msg.attach(MIMEText(
        render_template('emails/lottery_lose.txt', invoice=invoice, owner=owner),
        'plain', 'utf-8',
    ))
    _send_smtp(msg, app)


def check_lottery_redemptions(app):
    """Täglich prüfen ob Kunden ihren Gewinn-Code per E-Mail eingesendet haben."""
    with app.app_context():
        from app.models import LotteryEntry
        pending = LotteryEntry.query.filter_by(won=True, code_redeemed=False).count()
        if pending == 0:
            return
        try:
            _check_redemptions_inner(app)
        except Exception as e:
            app.logger.error(f'Gewinnspiel IMAP-Prüfung fehlgeschlagen: {e}')


def _check_redemptions_inner(app):
    from app.models import LotteryEntry
    from app import db

    with imaplib.IMAP4_SSL(app.config['MAIL_IMAP_SERVER'], app.config['MAIL_IMAP_PORT']) as imap:
        imap.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        imap.select('INBOX')
        _, msg_ids = imap.search(None, 'UNSEEN')

        for msg_id in msg_ids[0].split():
            _, msg_data = imap.fetch(msg_id, '(RFC822)')
            raw_msg = msg_data[0][1]
            parsed = emaillib.message_from_bytes(raw_msg)
            body = _extract_body(parsed)
            from_addr = parsed.get('From', '')

            for code in re.findall(r'\b(\d{6})\b', body):
                entry = LotteryEntry.query.filter_by(
                    won=True, code=code, code_redeemed=False
                ).first()
                if entry:
                    entry.code_redeemed = True
                    entry.julius_notified = True
                    db.session.commit()
                    _notify_julius(entry, from_addr, app)
                    break


def _extract_body(msg):
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode('utf-8', errors='replace')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode('utf-8', errors='replace')
    return body


def _notify_julius(entry, from_addr, app):
    invoice = entry.invoice
    owner = _owner(app)
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = app.config['JULIUS_EMAIL']
    msg['Subject'] = (
        f"Gewinnspiel eingeloest – {invoice.customer.name} / {invoice.invoice_number}"
    )
    msg.attach(MIMEText(
        render_template(
            'emails/lottery_redeemed.txt',
            invoice=invoice,
            owner=owner,
            entry=entry,
            from_addr=from_addr,
        ),
        'plain', 'utf-8',
    ))
    _send_smtp(msg, app)
