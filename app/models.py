from datetime import date
from app import db


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150))
    street = db.Column(db.String(200), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)

    invoices = db.relationship('Invoice', backref='customer', lazy=True)

    def __repr__(self):
        return f'<Customer {self.name}>'


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    default_price = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(30), nullable=False, default='pauschal')

    def __repr__(self):
        return f'<Service {self.name}>'


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    service_period = db.Column(db.String(100))
    status = db.Column(db.Enum('draft', 'sent', 'paid'), nullable=False, default='draft')
    sent_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    items = db.relationship(
        'InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan'
    )

    @property
    def total(self):
        return sum(float(item.quantity) * float(item.unit_price) for item in self.items)

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    quantity = db.Column(db.Numeric(8, 2), nullable=False, default=1)
    unit = db.Column(db.String(30), nullable=False, default='pauschal')
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    @property
    def total(self):
        return float(self.quantity) * float(self.unit_price)
