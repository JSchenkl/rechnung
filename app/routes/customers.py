from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import Customer

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
@login_required
def list():
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('customers/list.html', customers=customers)


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            company=request.form.get('company') or None,
            street=request.form['street'],
            postal_code=request.form['postal_code'],
            city=request.form['city'],
            email=request.form['email'],
            phone=request.form.get('phone') or None,
            notes=request.form.get('notes') or None,
        )
        db.session.add(customer)
        db.session.commit()
        flash(f'Kunde "{customer.name}" angelegt.', 'success')
        return redirect(url_for('customers.list'))
    return render_template('customers/form.html', customer=None)


@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.company = request.form.get('company') or None
        customer.street = request.form['street']
        customer.postal_code = request.form['postal_code']
        customer.city = request.form['city']
        customer.email = request.form['email']
        customer.phone = request.form.get('phone') or None
        customer.notes = request.form.get('notes') or None
        db.session.commit()
        flash(f'Kunde "{customer.name}" aktualisiert.', 'success')
        return redirect(url_for('customers.list'))
    return render_template('customers/form.html', customer=customer)


@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    customer = Customer.query.get_or_404(id)
    if customer.invoices:
        flash('Kunde kann nicht gelöscht werden – es existieren noch Rechnungen.', 'danger')
        return redirect(url_for('customers.list'))
    db.session.delete(customer)
    db.session.commit()
    flash('Kunde gelöscht.', 'success')
    return redirect(url_for('customers.list'))
