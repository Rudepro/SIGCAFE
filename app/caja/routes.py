from datetime import datetime, date
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import Venta, CierreCaja, db
from ..decorators import requiere_rol
from ..utils import registrar_auditoria
from ..extensions import limiter
from ..forms import CierreCajaForm, EmptyForm
from . import caja_bp

@caja_bp.route('/resumen')
@login_required
@requiere_rol('admin', 'cajero', 'vendedor')
def resumen():
    hoy = date.today()
    if current_user.rol == 'vendedor':
        ventas_hoy = Venta.query.filter(db.func.date(Venta.fecha_hora) == hoy, Venta.estado == 'completada', Venta.usuario_id == current_user.id).all()
    else:
        ventas_hoy = Venta.query.filter(db.func.date(Venta.fecha_hora) == hoy, Venta.estado == 'completada').all()
        
    total_dia = sum(v.total for v in ventas_hoy)
    
    # Agrupar por metodo
    metodos = {}
    for v in ventas_hoy:
        m = v.metodo_pago
        if m not in metodos:
            metodos[m] = {'cantidad': 0, 'total': 0.0}
        metodos[m]['cantidad'] += 1
        metodos[m]['total'] += v.total

    totales_lista = [{'metodo_pago': k, 'cantidad': v['cantidad'], 'total': v['total']} for k, v in metodos.items()]
    
    cierre_hoy = CierreCaja.query.filter_by(fecha=hoy).first()

    return render_template('caja/resumen.html', ventas_hoy=ventas_hoy, total_dia=total_dia, 
                           totales_por_metodo=totales_lista, hoy=hoy, cierre_hoy=cierre_hoy)


@caja_bp.route('/cierre', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin', 'cajero')
@limiter.limit("3 per minute")
def cierre():
    hoy = date.today()
    cierre_existente = CierreCaja.query.filter_by(fecha=hoy).first()
    if cierre_existente:
        flash('Ya se realizó un cierre de caja el día de hoy.', 'info')
        return redirect(url_for('caja.resumen'))

    ventas_hoy = Venta.query.filter(db.func.date(Venta.fecha_hora) == hoy, Venta.estado == 'completada').all()
    total_sistema = sum(v.total for v in ventas_hoy if v.metodo_pago == 'efectivo')
    num_ventas = len(ventas_hoy)

    form = CierreCajaForm()

    if form.validate_on_submit():
        efectivo_real = form.total_efectivo_real.data
        obs = form.observaciones.data
        diferencia = efectivo_real - total_sistema

        estado = 'CUADRADO'
        if abs(diferencia) >= 0.01:
            estado = 'FALTANTE' if diferencia < 0 else 'SOBRANTE'

        nuevo_cierre = CierreCaja(
            fecha=hoy, cajero_id=current_user.id,
            total_ventas_sistema=total_sistema,
            total_efectivo_real=efectivo_real,
            diferencia=diferencia,
            observaciones=obs,
            estado=estado
        )
        db.session.add(nuevo_cierre)
        db.session.commit()

        if estado != 'CUADRADO':
            registrar_auditoria('CIERRE_CAJA_DIFERENCIA', 'caja', f'Cierre con diferencia de ${diferencia}. Cajero: {current_user.email}')
        else:
            registrar_auditoria('CIERRE_CAJA', 'caja', f'Cierre cuadrado. Total: ${total_sistema}')

        flash(f'Cierre de caja registrado. Estado: {estado}', 'success' if estado == 'CUADRADO' else 'warning')
        return redirect(url_for('caja.resumen'))

    return render_template('caja/cierre.html', form=form, total_sistema=total_sistema, 
                           num_ventas=num_ventas, hoy=hoy)
