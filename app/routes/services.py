from types import SimpleNamespace

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models import Service

services_bp = Blueprint('services', __name__, url_prefix='/services')


def _parse_price(raw):
    raw = (raw or '').strip()
    if ',' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    return float(raw)


@services_bp.route('/')
@login_required
def list():
    services = Service.query.order_by(Service.name).all()
    return render_template('services/list.html', services=services)


@services_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            price = _parse_price(request.form['default_price'])
        except ValueError:
            flash(f'Ungültiger Preis "{request.form["default_price"]}".', 'danger')
            form_data = SimpleNamespace(
                name=request.form['name'], default_price=None, unit=request.form['unit']
            )
            return render_template('services/form.html', service=form_data)

        service = Service(
            name=request.form['name'],
            default_price=price,
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
        try:
            price = _parse_price(request.form['default_price'])
        except ValueError:
            flash(f'Ungültiger Preis "{request.form["default_price"]}".', 'danger')
            form_data = SimpleNamespace(
                name=request.form['name'], default_price=None, unit=request.form['unit']
            )
            return render_template('services/form.html', service=form_data)

        service.name = request.form['name']
        service.default_price = price
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
