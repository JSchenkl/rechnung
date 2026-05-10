from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Invoice, Customer

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    recent_invoices = Invoice.query.order_by(Invoice.issue_date.desc()).limit(10).all()
    open_invoices = Invoice.query.filter(Invoice.status.in_(['draft', 'sent'])).all()
    open_amount = sum(inv.total for inv in open_invoices)
    total_customers = Customer.query.count()
    return render_template(
        'dashboard.html',
        recent_invoices=recent_invoices,
        open_amount=open_amount,
        total_customers=total_customers,
    )
