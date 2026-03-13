from flask import Flask
from werkzeug.security import generate_password_hash

from config import Config
from models import db, User

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

    existing_user = User.query.filter_by(username="admin").first()
    if not existing_user:
        user = User(
            username="admin",
            password_hash=generate_password_hash("1234")
        )
        db.session.add(user)
        db.session.commit()
        print("Usuario creado: admin / 1234")
    else:
        print("El usuario admin ya existe.")