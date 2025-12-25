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
    app.run(debug=False)