import io
from datetime import date, timedelta, datetime

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, send_file, current_app, jsonify,
)
from flask_login import login_required

from app import db
from app.models import Invoice, InvoiceItem, Customer, Service
from app.email_utils import send_invoice_email, generate_pdf

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
    try:
        send_invoice_email(invoice)
        invoice.status = 'sent'
        invoice.sent_at = datetime.now()
        db.session.commit()
        flash(f'Rechnung erfolgreich an {invoice.customer.email} verschickt.', 'success')
    except Exception as e:
        flash(f'Fehler beim Versenden: {e}', 'danger')
    return redirect(url_for('invoices.detail', id=invoice.id))


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
