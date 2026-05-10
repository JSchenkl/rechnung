from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import Service

services_bp = Blueprint('services', __name__, url_prefix='/services')


@services_bp.route('/')
@login_required
def list():
    services = Service.query.order_by(Service.name).all()
    return render_template('services/list.html', services=services)


@services_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        service = Service(
            name=request.form['name'],
            default_price=float(request.form['default_price'].replace(',', '.')),
            unit=request.form['unit'],
        )
        db.session.add(service)
        db.session.commit()
        flash(f'Leistung "{service.name}" angelegt.', 'success')
        return redirect(url_for('services.list'))
    return render_template('services/form.html', service=None)


@services_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    service = Service.query.get_or_404(id)
    if request.method == 'POST':
        service.name = request.form['name']
        service.default_price = float(request.form['default_price'].replace(',', '.'))
        service.unit = request.form['unit']
        db.session.commit()
        flash(f'Leistung "{service.name}" aktualisiert.', 'success')
        return redirect(url_for('services.list'))
    return render_template('services/form.html', service=service)


@services_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    service = Service.query.get_or_404(id)
    db.session.delete(service)
    db.session.commit()
    flash('Leistung gelöscht.', 'success')
    return redirect(url_for('services.list'))
