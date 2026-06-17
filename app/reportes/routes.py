from datetime import datetime, date, timedelta
from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func
from ..models import Venta, DetalleVenta, Producto, Usuario, MovimientoInventario
from ..extensions import db
from ..decorators import requiere_rol
from . import reportes_bp


@reportes_bp.route('/')
@login_required
@requiere_rol('admin', 'cajero')
def index():
    # Date filters
    fecha_desde_str = request.args.get('fecha_desde', '')
    fecha_hasta_str = request.args.get('fecha_hasta', '')

    try:
        fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date() \
            if fecha_desde_str else date.today() - timedelta(days=30)
        fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date() \
            if fecha_hasta_str else date.today()
    except ValueError:
        fecha_desde = date.today() - timedelta(days=30)
        fecha_hasta = date.today()

    inicio = datetime.combine(fecha_desde, datetime.min.time())
    fin = datetime.combine(fecha_hasta, datetime.max.time())

    # Sales in range
    ventas = Venta.query.filter(
        Venta.fecha_hora.between(inicio, fin)
    ).order_by(Venta.fecha_hora.desc()).all()

    total_periodo = sum(v.total for v in ventas)
    num_ventas = len(ventas)

    # By payment method
    ventas_por_metodo = db.session.query(
        Venta.metodo_pago,
        func.count(Venta.id).label('cantidad'),
        func.sum(Venta.total).label('total')
    ).filter(
        Venta.fecha_hora.between(inicio, fin)
    ).group_by(Venta.metodo_pago).all()

    # Top products
    top_productos = db.session.query(
        Producto.nombre,
        func.sum(DetalleVenta.cantidad).label('total_vendido'),
        func.sum(DetalleVenta.subtotal).label('total_ingresos')
    ).join(DetalleVenta).join(Venta).filter(
        Venta.fecha_hora.between(inicio, fin)
    ).group_by(Producto.nombre).order_by(
        func.sum(DetalleVenta.subtotal).desc()
    ).limit(10).all()

    # By seller
    ventas_por_usuario = db.session.query(
        Usuario.nombre,
        func.count(Venta.id).label('cantidad'),
        func.sum(Venta.total).label('total')
    ).join(Venta, Venta.usuario_id == Usuario.id).filter(
        Venta.fecha_hora.between(inicio, fin)
    ).group_by(Usuario.nombre).order_by(
        func.sum(Venta.total).desc()
    ).all()

    # Stock summary
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()

    return render_template('reportes/index.html',
                           ventas=ventas,
                           total_periodo=total_periodo,
                           num_ventas=num_ventas,
                           ventas_por_metodo=ventas_por_metodo,
                           top_productos=top_productos,
                           ventas_por_usuario=ventas_por_usuario,
                           productos=productos,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)
