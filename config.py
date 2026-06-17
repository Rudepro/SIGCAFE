import os
import sys
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Load environment variables from .env
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        print("ERROR: SECRET_KEY no está definida en el entorno.")
        sys.exit(1)

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(DATA_DIR, "sigcafe.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('SESSION_MINUTES', 30)))
    
    # Anti-CSRF
    WTF_CSRF_ENABLED = True
    
    # File uploads / payload limits
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # Max 2MB request

    # Lockout parameters
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_MINUTES = int(os.environ.get('LOCKOUT_MINUTES', 15))


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False # Para desarrollo local sin HTTPS


class ProductionConfig(Config):
    DEBUG = False
    # En producción forzamos secure cookie y strict HSTS desde Flask-Talisman


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
