from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    loans = db.relationship("Loan", backref="client", cascade="all, delete-orphan", lazy=True)


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    amount_total = db.Column(db.Float, nullable=False)
    installment_count = db.Column(db.Integer, nullable=False)
    installment_value = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="activo", nullable=False)
    initial_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    installments = db.relationship("Installment", backref="loan", cascade="all, delete-orphan", lazy=True)

    @property
    def total_paid(self):
        return round(sum(i.amount for i in self.installments if i.status == "pagada"), 2)

    @property
    def balance(self):
        return round(max(self.amount_total - self.total_paid, 0), 2)


class Installment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pendiente", nullable=False)
    payment_date = db.Column(db.Date, nullable=True)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)