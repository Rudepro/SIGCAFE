import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, abort, render_template, request
from flask_login import current_user, logout_user
from flask_talisman import Talisman
from config import config_map

from .extensions import db, login_manager, csrf, limiter

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    cfg = config_map.get(config_name, config_map['default'])
    app.config.from_object(cfg)

    # Ensure data and logs directory exists
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # Security Logging
    handler = RotatingFileHandler(
        os.path.join(logs_dir, 'sigcafe_security.log'), 
        maxBytes=10_000_000,   # 10MB por archivo
        backupCount=5           # guardar 5 archivos historicos
    )
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Talisman Configuration
    csp = {
        'default-src': "'self'",
        'script-src': ["'self'", 'https://cdn.jsdelivr.net', "'unsafe-inline'"],
        'style-src': ["'self'", 'https://cdn.jsdelivr.net', 'https://fonts.googleapis.com', "'unsafe-inline'"],
        'font-src': ["'self'", 'https://fonts.gstatic.com', 'https://cdn.jsdelivr.net'],
        'img-src': ["'self'", 'data:'],
        'object-src': "'none'",
        'frame-ancestors': "'none'"
    }

    Talisman(app,
        force_https=(config_name == 'production'),
        strict_transport_security=True,
        session_cookie_secure=(config_name == 'production'),
        content_security_policy=csp,
        referrer_policy='strict-origin-when-cross-origin',
        feature_policy={
            'geolocation': "'none'",
            'camera': "'none'",
            'microphone': "'none'"
        }
    )

    with app.app_context():
        # Wal mode configuration for SQLite
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            from sqlalchemy import text
            db.session.execute(text('PRAGMA journal_mode=WAL;'))
            db.session.commit()
            
        db.create_all()

    # Before request hook to verify active user
    @app.before_request
    def verificar_usuario_activo():
        if current_user.is_authenticated and not current_user.activo:
            from .utils import registrar_auditoria
            registrar_auditoria('ACCESO_DENEGADO', 'seguridad', f'Usuario inactivo intento acceder: {current_user.email}')
            logout_user()
            abort(403)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors.html', error=404, msg="Página no encontrada."), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors.html', error=403, msg="Acceso denegado."), 403

    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f"Rate limit superado: {request.remote_addr} en {request.path}")
        from .utils import registrar_auditoria
        try:
            registrar_auditoria('RATE_LIMIT', 'seguridad', f"IP {request.remote_addr} supero el limite en {request.path}")
        except Exception:
            pass # Ignore if db context issues
        return render_template('errors.html', error=429, msg="Demasiadas peticiones. Intente más tarde."), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error("Error Interno (500)", exc_info=True)
        return render_template('errors.html', error=500, msg="Error interno del servidor."), 500

    @app.after_request
    def hide_server_header(response):
        response.headers['Server'] = 'SIGCAFE'
        return response

    # Register blueprints
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from .usuarios import usuarios_bp
    app.register_blueprint(usuarios_bp)

    from .productos import productos_bp
    app.register_blueprint(productos_bp)

    from .ventas import ventas_bp
    app.register_blueprint(ventas_bp)

    from .caja import caja_bp
    app.register_blueprint(caja_bp)

    from .inventario import inventario_bp
    app.register_blueprint(inventario_bp)

    from .promociones import promociones_bp
    app.register_blueprint(promociones_bp)

    from .reportes import reportes_bp
    app.register_blueprint(reportes_bp)

    from .auditoria import auditoria_bp
    app.register_blueprint(auditoria_bp)

    return app
