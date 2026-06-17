from functools import wraps
from flask import flash, redirect, url_for, abort, request
from flask_login import current_user

def requiere_rol(*roles):
    """Decorador que verifica si el usuario tiene uno de los roles permitidos."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión primero.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            if current_user.rol not in roles:
                # Security Audit log handled at a higher level or in route if needed, 
                # but simply denying access is sufficient here.
                from .utils import registrar_auditoria
                registrar_auditoria('ACCESO_DENEGADO', 'seguridad', f'Intento de acceso a ruta no autorizada: {request.path}')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def verificar_propiedad(model, id_kwarg, user_id_field='usuario_id', admin_override=True):
    """
    Verifica que el recurso solicitado pertenezca al usuario actual.
    Si admin_override es True, un admin puede acceder a cualquier recurso.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            recurso_id = kwargs.get(id_kwarg)
            if recurso_id:
                recurso = model.query.get_or_404(recurso_id)
                owner_id = getattr(recurso, user_id_field, None)
                
                is_owner = (owner_id == current_user.id)
                is_admin = (admin_override and current_user.rol == 'admin')
                
                if not (is_owner or is_admin):
                    from .utils import registrar_auditoria
                    registrar_auditoria('ACCESO_DENEGADO', 'seguridad', f'Intento de acceso a recurso ajeno ({model.__name__} {recurso_id})')
                    abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
