from flask import Blueprint

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

from . import routes  # noqa: F401, E402
