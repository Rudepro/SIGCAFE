from flask import Blueprint

auditoria_bp = Blueprint('auditoria', __name__, url_prefix='/auditoria')

from . import routes  # noqa: F401, E402
