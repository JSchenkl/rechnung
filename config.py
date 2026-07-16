import os
import subprocess
from dotenv import load_dotenv

load_dotenv()


def _get_commit_sha():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        pass
    try:
        with open(os.path.join(os.path.dirname(__file__), 'COMMIT')) as f:
            return f.read().strip()[:7]
    except Exception:
        return 'unknown'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'mysql+pymysql://rechnung:password@localhost/rechnung'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'rechnung@julius.schenkl.de')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')

    MAIL_IMAP_SERVER = os.environ.get('MAIL_IMAP_SERVER', 'imap.strato.de')
    MAIL_IMAP_PORT = int(os.environ.get('MAIL_IMAP_PORT', '993'))

    JULIUS_EMAIL = os.environ.get('JULIUS_EMAIL', 'julius@schenkl.de')

    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

    OWNER_NAME = os.environ.get('OWNER_NAME', 'Julius Schenkl')
    OWNER_STREET = os.environ.get('OWNER_STREET', '')
    OWNER_POSTAL_CODE = os.environ.get('OWNER_POSTAL_CODE', '')
    OWNER_CITY = os.environ.get('OWNER_CITY', '')
    OWNER_IBAN = os.environ.get('OWNER_IBAN', '')
    OWNER_EMAIL = os.environ.get('MAIL_USERNAME', 'rechnung@julius.schenkl.de')

    COMMIT_SHA = _get_commit_sha()

    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
