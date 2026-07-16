import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
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

    _setup_logging(app)

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

    @app.errorhandler(500)
    def handle_internal_error(error):
        # Flask loggt den vollen Traceback bereits selbst (app.logger, siehe _setup_logging)
        return render_template('500.html'), 500

    # Tägliche Gewinnspiel-Prüfung per IMAP
    # Im Debug-Modus nur im Haupt-Prozess starten (nicht im Werkzeug-Reloader-Watcher)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        _start_lottery_scheduler(app)

    return app


def _setup_logging(app):
    log_file = app.config['LOG_FILE']
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(module)s] %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)


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
