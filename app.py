from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_file
)

from werkzeug.security import check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import Config
from models import db, User, Client, Loan, Installment


app = Flask(__name__)
@app.template_filter("gs")
def format_guaranies(value):
    try:
        return "{:,.0f}".format(value).replace(",", ".")
    except:
        return value
app.config.from_object(Config)
db.init_app(app)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("clients"))

        flash("Usuario o contraseña incorrectos.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def clients():

    all_clients = Client.query.order_by(Client.created_at.desc()).all()

    return render_template(
        "clients.html",
        clients=all_clients
    )


@app.route("/clients/new", methods=["GET", "POST"])
@login_required
def new_client():

    if request.method == "POST":

        client = Client(
            name=request.form["name"].strip(),
            phone=request.form.get("phone", "").strip(),
            address=request.form.get("address", "").strip(),
            notes=request.form.get("notes", "").strip()
        )

        db.session.add(client)
        db.session.commit()

        flash("Cliente creado correctamente.")

        return redirect(
            url_for("client_detail", client_id=client.id)
        )

    return render_template("new_client.html")


@app.route("/clients/<int:client_id>")
@login_required
def client_detail(client_id):

    client = Client.query.get_or_404(client_id)

    total_amount = sum(loan.amount_total for loan in client.loans)
    total_paid = sum(loan.total_paid for loan in client.loans)
    total_balance = sum(loan.balance for loan in client.loans)

    return render_template(
        "client_detail.html",
        client=client,
        total_amount=total_amount,
        total_paid=total_paid,
        total_balance=total_balance
    )


@app.route("/clients/<int:client_id>/loans/new", methods=["GET", "POST"])
@login_required
def new_loan(client_id):

    client = Client.query.get_or_404(client_id)

    if request.method == "POST":

        amount_total = float(request.form["amount_total"])
        installment_count = int(request.form["installment_count"])

        installment_value = round(
            amount_total / installment_count,
            2
        )

        loan = Loan(
            client_id=client.id,
            amount_total=amount_total,
            installment_count=installment_count,
            installment_value=installment_value,
            start_date=datetime.strptime(
                request.form["start_date"],
                "%Y-%m-%d"
            ).date(),
            initial_note=request.form.get(
                "initial_note", ""
            ).strip()
        )

        db.session.add(loan)
        db.session.commit()

        for n in range(1, installment_count + 1):

            installment = Installment(
                loan_id=loan.id,
                number=n,
                amount=installment_value,
                status="pendiente"
            )

            db.session.add(installment)

        db.session.commit()

        flash("Préstamo y cuotas creados correctamente.")

        return redirect(
            url_for("client_detail", client_id=client.id)
        )

    return render_template(
        "new_loan.html",
        client=client
    )


@app.route("/installments/<int:installment_id>/pay",
           methods=["GET", "POST"])
@login_required
def pay_installment(installment_id):

    installment = Installment.query.get_or_404(
        installment_id
    )

    loan = installment.loan

    if request.method == "POST":

        installment.status = "pagada"

        installment.payment_date = datetime.strptime(
            request.form["payment_date"],
            "%Y-%m-%d"
        ).date()

        installment.note = request.form.get(
            "note", ""
        ).strip()

        db.session.commit()

        if all(i.status == "pagada"
               for i in loan.installments):

            loan.status = "cancelado"
            db.session.commit()

        flash("Cuota pagada correctamente.")

        return redirect(
            url_for(
                "client_detail",
                client_id=loan.client_id
            )
        )

    return render_template(
        "pay_installment.html",
        installment=installment
    )


@app.route("/clients/<int:client_id>/export-pdf")
@login_required
def export_client_pdf(client_id):

    client = Client.query.get_or_404(client_id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(
        40,
        y,
        f"Ficha cliente: {client.name}"
    )

    y -= 30

    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        40,
        y,
        f"Telefono: {client.phone or '-'}"
    )

    y -= 15

    pdf.drawString(
        40,
        y,
        f"Direccion: {client.address or '-'}"
    )

    y -= 25

    for loan in client.loans:

        pdf.setFont("Helvetica-Bold", 12)

        pdf.drawString(
            40,
            y,
            f"Prestamo #{loan.id}"
        )

        y -= 20

        pdf.setFont("Helvetica", 10)

        pdf.drawString(
    40,
    y,
    f"Monto total: {'{:,.0f}'.format(loan.amount_total).replace(',', '.')}"
)

        y -= 15

        pdf.drawString(
            40,
            y,
            f"Cantidad cuotas: {loan.installment_count}"
        )

        y -= 15

        pdf.drawString(
    40,
    y,
    f"Valor cuota: {'{:,.0f}'.format(loan.installment_value).replace(',', '.')}"
)

        y -= 20

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, y, "Cuotas")

        y -= 15

        pdf.setFont("Helvetica", 10)

        for inst in loan.installments:

            texto = (
    f"Cuota {inst.number} | "
    f"{'{:,.0f}'.format(inst.amount).replace(',', '.')} | "
    f"{inst.status}"
)

            pdf.drawString(40, y, texto)

            y -= 15

        y -= 15

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"cliente_{client.id}.pdf",
        mimetype="application/pdf"
    )


@app.route("/installments/<int:installment_id>/update", methods=["POST"])
@login_required
def update_installment(installment_id):

    installment = Installment.query.get_or_404(installment_id)
    loan = installment.loan

    action = request.form.get("action")
    note = request.form.get("note", "").strip()

    installment.note = note

    if action == "mark_paid":
        installment.status = "pagada"
        installment.payment_date = datetime.today().date()

    elif action == "mark_pending":
        installment.status = "pendiente"
        installment.payment_date = None

    db.session.commit()

    if all(i.status == "pagada" for i in loan.installments):
        loan.status = "cancelado"
    else:
        loan.status = "activo"

    db.session.commit()

    flash("Cuota actualizada correctamente.")

    return redirect(url_for("client_detail", client_id=loan.client_id))

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)