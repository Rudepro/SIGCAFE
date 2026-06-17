from flask import Blueprint

promociones_bp = Blueprint('promociones', __name__, url_prefix='/promociones')

from . import routes  # noqa: F401, E402
