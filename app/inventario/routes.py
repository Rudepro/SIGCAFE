from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..models import Producto, MovimientoInventario
from ..extensions import db, limiter
from ..decorators import requiere_rol
from ..utils import registrar_auditoria
from ..forms import MovimientoInventarioForm
from . import inventario_bp

@inventario_bp.route('/')
@login_required
@requiere_rol('admin', 'bodeguero', 'cocina')
def lista():
    productos = Producto.query.filter(Producto.categoria != 'combo', Producto.activo == True).all()
    return render_template('inventario/lista.html', productos=productos)

@inventario_bp.route('/movimiento', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin', 'bodeguero', 'cocina')
@limiter.limit("10 per minute")
def movimiento():
    productos = Producto.query.filter(Producto.categoria != 'combo', Producto.activo == True).order_by(Producto.nombre).all()
    form = MovimientoInventarioForm()

    if form.validate_on_submit():
        producto_id = form.producto_id.data
        tipo = form.tipo.data
        cantidad = form.cantidad.data
        motivo = form.motivo.data

        if current_user.rol == 'cocina' and tipo != 'salida':
            flash('Acceso denegado: Cocina solo puede registrar salidas.', 'danger')
            return redirect(url_for('inventario.movimiento'))

        producto = Producto.query.get(producto_id)
        if not producto or not producto.activo:
            flash('Producto inválido.', 'danger')
            return redirect(url_for('inventario.movimiento'))

        if tipo == 'salida' and producto.stock_actual < cantidad:
            flash(f'Error: Stock insuficiente. El stock actual es {producto.stock_actual}.', 'danger')
            return render_template('inventario/movimiento.html', productos=productos, form=form, motivos=[])

        # Actualizar stock
        if tipo == 'entrada':
            producto.stock_actual += cantidad
        else:
            producto.stock_actual -= cantidad

        movimiento = MovimientoInventario(
            producto_id=producto.id, tipo=tipo,
            cantidad=cantidad, motivo=motivo,
            usuario_id=current_user.id
        )
        db.session.add(movimiento)
        db.session.commit()

        registrar_auditoria('MOVIMIENTO_INVENTARIO', 'inventario', f'{tipo.upper()} de {cantidad} {producto.unidad_medida}s - {producto.nombre}')
        flash('Movimiento de inventario registrado.', 'success')
        return redirect(url_for('inventario.lista'))

    # Preparar motivos rápidos
    motivos = [
        'Compra a proveedor', 'Ajuste de inventario positivo', 'Devolución de cliente'
    ] if current_user.rol != 'cocina' else []
    motivos += [
        'Uso en cocina', 'Merma / Desperdicio', 'Producto caducado', 'Ajuste de inventario negativo'
    ]

    return render_template('inventario/movimiento.html', productos=productos, form=form, motivos=motivos)

@inventario_bp.route('/historial')
@login_required
@requiere_rol('admin', 'bodeguero')
def historial():
    movimientos = MovimientoInventario.query.order_by(MovimientoInventario.fecha_hora.desc()).all()
    return render_template('inventario/historial.html', movimientos=movimientos)
