from flask import Flask
from routes.base import base_bp
from routes.auth import auth_bp
from routes.client import client_bp
from routes.cashier import cashier_bp
from routes.admin import admin_bp
from models.models import db, User
from libs.libs import hash_password

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fly.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super_secret'

app.register_blueprint(base_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(client_bp)
app.register_blueprint(cashier_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        db.create_all()
        stmt = db.select(User).where(User.phone == "+7 (000) 000-00-00")
        user = db.session.execute(stmt).scalar()
        if not user:
            admin = User(
                name = "admin",
                surname = "admin",
                patronymic = "admin",
                passport_series = "0000",
                passport_number = "000000",
                phone = "+7 (000) 000-00-00",
                password = hash_password("admin123"),
                role = 'admin'
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)