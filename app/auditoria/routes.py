from flask import render_template, request
from flask_login import login_required
from ..models import Auditoria
from ..decorators import requiere_rol
from . import auditoria_bp


@auditoria_bp.route('/')
@login_required
@requiere_rol('admin')
def index():
    pagina = request.args.get('pagina', 1, type=int)
    modulo_filtro = request.args.get('modulo', '')
    accion_filtro = request.args.get('accion', '')

    query = Auditoria.query.order_by(Auditoria.fecha_hora.desc())

    if modulo_filtro:
        query = query.filter(Auditoria.modulo == modulo_filtro)
    if accion_filtro:
        query = query.filter(Auditoria.accion.ilike(f'%{accion_filtro}%'))

    registros = query.limit(300).all()

    # For filter dropdowns
    modulos = ['auth', 'ventas', 'caja', 'inventario', 'productos',
               'usuarios', 'promociones', 'reportes']
    acciones = [r.accion for r in Auditoria.query.with_entities(
        Auditoria.accion).distinct().all()]

    return render_template('auditoria/index.html',
                           registros=registros,
                           modulos=modulos,
                           acciones=sorted(set(acciones)),
                           modulo_filtro=modulo_filtro,
                           accion_filtro=accion_filtro)
