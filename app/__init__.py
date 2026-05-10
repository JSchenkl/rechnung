from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name='default'):
    from config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte anmelden.'
    login_manager.login_message_category = 'warning'

    from app.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.customers import customers_bp
    from app.routes.services import services_bp
    from app.routes.invoices import invoices_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(invoices_bp)

    return app
