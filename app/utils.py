from datetime import datetime
from flask import request, current_app
from .extensions import db
from .models import Auditoria
from flask_login import current_user


def registrar_auditoria(accion, modulo, descripcion=None):
    """Registra una acción en el log de auditoría en BD y en archivo de log de seguridad."""
    try:
        usuario_id = current_user.id if current_user and current_user.is_authenticated else None
        usuario_nombre = current_user.email if current_user and current_user.is_authenticated else "SISTEMA"
        ip = request.remote_addr if request else "0.0.0.0"
        
        # Log to BD
        log = Auditoria(
            usuario_id=usuario_id,
            accion=accion,
            modulo=modulo,
            descripcion=descripcion,
            ip_address=ip,
            fecha_hora=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        # Log to file
        log_msg = f"User: {usuario_nombre} | IP: {ip} | Module: {modulo} | Action: {accion} | Desc: {descripcion}"
        if accion in ['LOGIN_FALLIDO', 'ACCESO_DENEGADO', 'CUENTA_BLOQUEADA', 'RATE_LIMIT']:
            current_app.logger.warning(log_msg)
        else:
            current_app.logger.info(log_msg)
            
    except Exception as e:
        db.session.rollback()
        try:
            current_app.logger.error(f"Error registrando auditoria: {str(e)} | Action: {accion}", exc_info=True)
        except Exception:
            pass
