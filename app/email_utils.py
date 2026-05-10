import io
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

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

    context = ssl.create_default_context()
    server_host = app.config['MAIL_SERVER']
    server_port = app.config['MAIL_PORT']
    use_tls = app.config['MAIL_USE_TLS']
    username = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']

    if use_tls:
        with smtplib.SMTP(server_host, server_port) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(server_host, server_port, context=context) as server:
            server.login(username, password)
            server.send_message(msg)
