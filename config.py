import os
from dotenv import load_dotenv

load_dotenv()


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

    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

    OWNER_NAME = os.environ.get('OWNER_NAME', 'Julius Schenkl')
    OWNER_STREET = os.environ.get('OWNER_STREET', '')
    OWNER_POSTAL_CODE = os.environ.get('OWNER_POSTAL_CODE', '')
    OWNER_CITY = os.environ.get('OWNER_CITY', '')
    OWNER_IBAN = os.environ.get('OWNER_IBAN', '')
    OWNER_EMAIL = os.environ.get('MAIL_USERNAME', 'rechnung@julius.schenkl.de')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
