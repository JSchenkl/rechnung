import io
import csv
import re
from datetime import date, timedelta, datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, send_file, current_app, jsonify,
)
from flask_login import login_required

from app import db
from app.models import Invoice, InvoiceItem, Customer, Service
from app.email_utils import send_invoice_email, generate_pdf, run_lottery_draw

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')


def _next_invoice_number():
    year = datetime.now().year
    last = (
        Invoice.query
        .filter(Invoice.invoice_number.like(f'{year}-%'))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    num = int(last.invoice_number.split('-')[1]) + 1 if last else 1
    return f'{year}-{num:03d}'


@invoices_bp.route('/')
@login_required
def list():
    status = request.args.get('status', '')
    query = Invoice.query.order_by(Invoice.issue_date.desc())
    if status:
        query = query.filter(Invoice.status == status)
    invoices = query.all()
    return render_template('invoices/list.html', invoices=invoices, status_filter=status)


@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    customers = Customer.query.order_by(Customer.name).all()
    services = Service.query.order_by(Service.name).all()

    if request.method == 'POST':
        due_str = request.form.get('due_date')
        issue_date = date.today()
        due_date = date.fromisoformat(due_str) if due_str else issue_date + timedelta(days=14)

        invoice = Invoice(
            invoice_number=_next_invoice_number(),
            customer_id=int(request.form['customer_id']),
            issue_date=issue_date,
            due_date=due_date,
            service_period=request.form.get('service_period') or None,
            notes=request.form.get('notes') or None,
        )
        db.session.add(invoice)
        db.session.flush()

        descriptions = request.form.getlist('description')
        quantities = request.form.getlist('quantity')
        units = request.form.getlist('unit')
        prices = request.form.getlist('unit_price')

        for desc, qty, unit, price in zip(descriptions, quantities, units, prices):
            if desc.strip() and price.strip():
                db.session.add(InvoiceItem(
                    invoice_id=invoice.id,
                    description=desc.strip(),
                    quantity=float(qty.replace(',', '.') or '1'),
                    unit=unit or 'pauschal',
                    unit_price=float(price.replace(',', '.')),
                ))

        db.session.commit()
        flash(f'Rechnung {invoice.invoice_number} erstellt.', 'success')
        return redirect(url_for('invoices.detail', id=invoice.id))

    default_due = (date.today() + timedelta(days=14)).isoformat()
    return render_template(
        'invoices/form.html',
        customers=customers,
        services=services,
        default_due=default_due,
        next_number=_next_invoice_number(),
    )


@invoices_bp.route('/<int:id>')
@login_required
def detail(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/detail.html', invoice=invoice)


@invoices_bp.route('/<int:id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(id):
    invoice = Invoice.query.get_or_404(id)
    invoice.status = 'paid'
    db.session.commit()
    flash('Rechnung als bezahlt markiert.', 'success')
    return redirect(url_for('invoices.detail', id=invoice.id))


@invoices_bp.route('/<int:id>/pdf')
@login_required
def pdf(id):
    invoice = Invoice.query.get_or_404(id)
    pdf_bytes = generate_pdf(invoice)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Rechnung_{invoice.invoice_number}.pdf',
    )


@invoices_bp.route('/<int:id>/send', methods=['POST'])
@login_required
def send(id):
    invoice = Invoice.query.get_or_404(id)
    invoice.lottery = 'lottery' in request.form
    db.session.commit()

    try:
        send_invoice_email(invoice)
        invoice.status = 'sent'
        invoice.sent_at = datetime.now()
        db.session.commit()
        flash(f'Rechnung erfolgreich an {invoice.customer.email} verschickt.', 'success')
    except Exception as e:
        flash(f'Fehler beim Versenden: {e}', 'danger')
        return redirect(url_for('invoices.detail', id=invoice.id))

    if invoice.lottery and not invoice.lottery_entry:
        try:
            run_lottery_draw(invoice)
        except Exception as e:
            current_app.logger.error(f'Gewinnspiel-Auslosung fehlgeschlagen (Rechnung {invoice.id}): {e}')

    return redirect(url_for('invoices.detail', id=invoice.id))


@invoices_bp.route('/import-csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    if request.method == 'GET':
        return render_template('invoices/import_csv.html')

    file = request.files.get('csv_file')
    if not file or not file.filename:
        flash('Bitte eine CSV-Datei auswählen.', 'danger')
        return redirect(url_for('invoices.import_csv'))

    try:
        raw = file.read()
        # Comdirect exports in Latin-1
        try:
            content = raw.decode('latin-1')
        except UnicodeDecodeError:
            content = raw.decode('utf-8', errors='replace')
    except Exception as e:
        flash(f'Fehler beim Lesen der Datei: {e}', 'danger')
        return redirect(url_for('invoices.import_csv'))

    # Find the header row (contains "Buchungstag")
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if 'Buchungstag' in line:
            header_idx = i
            break

    if header_idx is None:
        flash('Ungültiges Dateiformat – keine Comdirect-Kontoauszugsdatei erkannt.', 'danger')
        return redirect(url_for('invoices.import_csv'))

    data_lines = '\n'.join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(data_lines), delimiter=';',
                            quotechar='"', skipinitialspace=True)

    # Load open (sent) invoices
    open_invoices = Invoice.query.filter(Invoice.status == 'sent').all()
    invoice_map = {inv.invoice_number: inv for inv in open_invoices}

    marked = []
    skipped = []

    for row in reader:
        # Stop at trailing empty/summary rows Comdirect appends
        buchungstag = (row.get('Buchungstag') or '').strip().strip('"')
        if not buchungstag or buchungstag.startswith('"') or len(buchungstag) < 8:
            continue

        buchungstext = ' '.join([
            row.get('Buchungstext') or '',
            row.get('Vorgang') or '',
        ]).strip()

        matched_inv = None
        for inv_number, inv in invoice_map.items():
            # Match invoice number pattern (e.g. 2026-001) in the payment reference
            if re.search(re.escape(inv_number), buchungstext, re.IGNORECASE):
                matched_inv = inv
                break

        if matched_inv:
            matched_inv.status = 'paid'
            marked.append(matched_inv.invoice_number)
            del invoice_map[matched_inv.invoice_number]
        else:
            skipped.append(buchungstext[:80] if buchungstext else buchungstag)

    db.session.commit()

    if marked:
        flash(f'{len(marked)} Rechnung(en) als bezahlt markiert: {", ".join(marked)}', 'success')
    else:
        flash('Keine offenen Rechnungen in der Datei gefunden.', 'warning')

    return redirect(url_for('invoices.list'))


@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    invoice = Invoice.query.get_or_404(id)
    if invoice.status == 'sent':
        flash('Bereits versendete Rechnungen können nicht gelöscht werden.', 'danger')
        return redirect(url_for('invoices.detail', id=invoice.id))
    db.session.delete(invoice)
    db.session.commit()
    flash('Rechnung gelöscht.', 'success')
    return redirect(url_for('invoices.list'))
