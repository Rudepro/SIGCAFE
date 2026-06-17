from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario
from ..extensions import db, limiter
from ..utils import registrar_auditoria
from ..forms import LoginForm
from . import auth_bp


def es_url_segura(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Use generic message to prevent user enumeration
        generic_error = 'Credenciales inválidas.'

        usuario = Usuario.query.filter_by(email=email).first()

        # Evitar timing attacks
        if not usuario:
            from werkzeug.security import check_password_hash
            # Hash dummy
            check_password_hash('pbkdf2:sha256:600000$dummy$dummy', password)
            registrar_auditoria('LOGIN_FALLIDO', 'auth', f'Intento con email inexistente: {email}')
            flash(generic_error, 'danger')
            return render_template('auth/login.html', form=form)

        if not usuario.activo:
            registrar_auditoria('LOGIN_FALLIDO', 'auth', f'Usuario inactivo intento login: {email}')
            flash(generic_error, 'danger')
            return render_template('auth/login.html', form=form)

        if usuario.is_locked():
            registrar_auditoria('CUENTA_BLOQUEADA', 'auth', f'Intento en cuenta bloqueada: {email}')
            flash('Demasiados intentos fallidos. Cuenta bloqueada temporalmente.', 'danger')
            return render_template('auth/login.html', form=form)

        if usuario.check_password(password):
            usuario.login_intentos = 0
            usuario.bloqueado_hasta = None
            db.session.commit()

            # Session Fixation protection: regenerate session id implicitly by clearing and restoring necessary keys
            session.clear()
            
            login_user(usuario)
            registrar_auditoria('LOGIN_EXITOSO', 'auth', f'Usuario {usuario.nombre} inició sesión')
            flash('Inicio de sesión exitoso.', 'success')

            next_page = request.args.get('next')
            if not next_page or not es_url_segura(next_page):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        else:
            usuario.login_intentos += 1
            if usuario.login_intentos >= current_app.config['MAX_LOGIN_ATTEMPTS']:
                usuario.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=current_app.config['LOCKOUT_MINUTES'])
                registrar_auditoria('CUENTA_BLOQUEADA', 'auth', f'Cuenta bloqueada por múltiples intentos: {email}')
            else:
                registrar_auditoria('LOGIN_FALLIDO', 'auth', f'Intento fallido {usuario.login_intentos} para: {email}')
            
            db.session.commit()
            flash(generic_error, 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    nombre = current_user.nombre
    registrar_auditoria('LOGOUT', 'auth', f'Usuario {nombre} cerró sesión')
    logout_user()
    session.clear() # Invalidar sesión completamente
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))
