import json
from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ..models import Venta, DetalleVenta, Producto, Promocion, InsumoCombo
from ..extensions import db, limiter
from ..decorators import requiere_rol
from ..utils import registrar_auditoria
from ..forms import VentaForm, EmptyForm
from . import ventas_bp

def get_promocion_activa():
    ahora = datetime.utcnow().time()
    promos = Promocion.query.filter_by(activo=True).all()
    for p in promos:
        if p.hora_inicio and p.hora_fin:
            if p.hora_inicio <= ahora <= p.hora_fin:
                return p
        else:
            return p
    return None

@ventas_bp.route('/')
@login_required
@requiere_rol('admin', 'cajero', 'vendedor')
def historial():
    if current_user.rol == 'vendedor':
        ventas = Venta.query.filter_by(usuario_id=current_user.id).order_by(Venta.fecha_hora.desc()).all()
    else:
        ventas = Venta.query.order_by(Venta.fecha_hora.desc()).all()
    form = EmptyForm()
    return render_template('ventas/historial.html', ventas=ventas, form=form)

@ventas_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin', 'cajero', 'vendedor')
@limiter.limit("10 per minute")
def nueva():
    productos = Producto.query.filter_by(activo=True).all()
    promo_activa = get_promocion_activa()
    form = VentaForm()

    if form.validate_on_submit():
        metodo_pago = form.metodo_pago.data
        items_json = form.items.data
        
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            flash('Error en los datos enviados.', 'danger')
            return redirect(url_for('ventas.nueva'))

        if not items:
            flash('El carrito está vacío.', 'danger')
            return redirect(url_for('ventas.nueva'))

        venta = Venta(usuario_id=current_user.id, metodo_pago=metodo_pago)
        db.session.add(venta)
        db.session.flush() # Para obtener ID

        subtotal_venta = 0.0
        
        for item in items:
            p_id = int(item.get('producto_id', 0))
            cant = float(item.get('cantidad', 0))
            
            producto = Producto.query.get(p_id)
            if not producto or not producto.activo:
                db.session.rollback()
                flash(f'Producto no válido.', 'danger')
                return redirect(url_for('ventas.nueva'))

            # Validación de stock
            if producto.categoria != 'combo':
                if producto.stock_actual < cant:
                    db.session.rollback()
                    flash(f'Stock insuficiente para {producto.nombre}.', 'danger')
                    return redirect(url_for('ventas.nueva'))
                producto.stock_actual -= cant
            else:
                # Es un combo, descontar insumos
                insumos = InsumoCombo.query.filter_by(producto_combo_id=producto.id).all()
                for ins in insumos:
                    ins_prod = ins.insumo
                    cant_req = ins.cantidad_necesaria * cant
                    if ins_prod.stock_actual < cant_req:
                        db.session.rollback()
                        flash(f'Stock insuficiente del insumo {ins_prod.nombre} para armar el combo.', 'danger')
                        return redirect(url_for('ventas.nueva'))
                    ins_prod.stock_actual -= cant_req

            subtotal_item = cant * producto.precio
            subtotal_venta += subtotal_item

            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=cant,
                precio_unitario=producto.precio,
                subtotal=subtotal_item
            )
            db.session.add(detalle)

        # Aplicar descuento si aplica
        total_final = subtotal_venta
        if promo_activa and promo_activa.tipo == 'descuento':
            descuento = subtotal_venta * (promo_activa.valor / 100)
            total_final -= descuento
            
        venta.total = total_final
        db.session.commit()

        registrar_auditoria('REGISTRO_VENTA', 'ventas', f'Venta {venta.numero_transaccion} por ${venta.total}')
        flash('Venta registrada exitosamente.', 'success')
        return redirect(url_for('ventas.detalle', venta_id=venta.id))

    # Actualizar combos si falta insumo
    for p in productos:
        if p.categoria == 'combo':
            p.stock_actual = 9999
            for ins in p.combos_como_combo:
                max_posible = ins.insumo.stock_actual / ins.cantidad_necesaria
                if max_posible < p.stock_actual:
                    p.stock_actual = int(max_posible)

    return render_template('ventas/nueva.html', form=form, productos=productos, 
                           promo_activa=promo_activa, metodos_pago=[('efectivo','Efectivo'),('tarjeta','Tarjeta'),('transferencia','Transferencia')])

@ventas_bp.route('/detalle/<int:venta_id>')
@login_required
@requiere_rol('admin', 'cajero', 'vendedor')
def detalle(venta_id):
    venta = Venta.query.get_or_404(venta_id)
    
    # Ownership Check
    if venta.usuario_id != current_user.id and current_user.rol != 'admin':
        registrar_auditoria('ACCESO_DENEGADO', 'seguridad', f'Vendedor {current_user.email} intentó ver venta de otro')
        abort(403)
        
    detalles = venta.detalles.all()
    return render_template('ventas/detalle.html', venta=venta, detalles=detalles)

@ventas_bp.route('/eliminar/<int:venta_id>', methods=['POST'])
@login_required
@requiere_rol('admin')
def eliminar(venta_id):
    form = EmptyForm()
    if form.validate_on_submit():
        venta = Venta.query.get_or_404(venta_id)
        num = venta.numero_transaccion
        total = venta.total
        
        # Devolver stock
        for d in venta.detalles:
            p = d.producto
            if p:
                if p.categoria != 'combo':
                    p.stock_actual += d.cantidad
                else:
                    for ins in p.combos_como_combo:
                        ins.insumo.stock_actual += (ins.cantidad_necesaria * d.cantidad)

        venta.estado = 'anulada'
        db.session.commit()
        registrar_auditoria('ANULAR_VENTA', 'ventas', f'Venta {num} por ${total} anulada')
        flash('Venta anulada y stock restaurado.', 'warning')
    return redirect(url_for('ventas.historial'))
