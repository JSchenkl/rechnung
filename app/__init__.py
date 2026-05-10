import os

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

    # Tägliche Gewinnspiel-Prüfung per IMAP
    # Im Debug-Modus nur im Haupt-Prozess starten (nicht im Werkzeug-Reloader-Watcher)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        _start_lottery_scheduler(app)

    return app


def _start_lottery_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    from app.email_utils import check_lottery_redemptions

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        func=check_lottery_redemptions,
        args=[app],
        trigger='cron',
        hour=9,
        minute=0,
        id='lottery_check',
        replace_existing=True,
    )
    scheduler.start()
