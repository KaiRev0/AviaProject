import os
from flask import Flask
from routes.base import base_bp
from routes.auth import auth_bp
from routes.client import client_bp
from routes.cashier import cashier_bp
from routes.admin import admin_bp
from models.models import db

app = Flask(__name__) 

database_url = os.environ.get('DATABASE_URL', 'sqlite:///fly.db')

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super_secret')

db.init_app(app) 

app.register_blueprint(base_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(client_bp)
app.register_blueprint(cashier_bp)
app.register_blueprint(admin_bp)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=False)