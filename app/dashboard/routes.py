from flask import render_template
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from ..models import Venta, Producto, CierreCaja
from ..extensions import db
from . import dashboard_bp


@dashboard_bp.route('/')
@login_required
def index():
    hoy = date.today()
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    fin_dia = datetime.combine(hoy, datetime.max.time())

    # Ventas del día
    if current_user.rol == 'vendedor':
        ventas_hoy = Venta.query.filter(
            Venta.fecha_hora.between(inicio_dia, fin_dia),
            Venta.usuario_id == current_user.id
        ).all()
    else:
        ventas_hoy = Venta.query.filter(
            Venta.fecha_hora.between(inicio_dia, fin_dia)
        ).all()

    total_ventas = sum(v.total for v in ventas_hoy)
    num_ventas = len(ventas_hoy)

    # Alertas de stock bajo
    productos_stock_bajo = Producto.query.filter(
        Producto.activo == True,
        Producto.stock_actual <= Producto.stock_minimo
    ).all()

    # Productos próximos a vencer (7 días)
    hoy_plus7 = hoy + timedelta(days=7)
    productos_por_vencer = Producto.query.filter(
        Producto.activo == True,
        Producto.fecha_vencimiento != None,
        Producto.fecha_vencimiento <= hoy_plus7,
        Producto.fecha_vencimiento >= hoy
    ).all()

    # Último cierre de caja
    ultimo_cierre = CierreCaja.query.order_by(CierreCaja.fecha.desc()).first()

    return render_template(
        'dashboard/index.html',
        ventas_hoy=ventas_hoy,
        total_ventas=total_ventas,
        num_ventas=num_ventas,
        productos_stock_bajo=productos_stock_bajo,
        productos_por_vencer=productos_por_vencer,
        ultimo_cierre=ultimo_cierre
    )
