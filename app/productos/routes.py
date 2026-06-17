from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from ..models import Producto
from ..extensions import db, limiter
from ..decorators import requiere_rol
from ..utils import registrar_auditoria
from ..forms import ProductoForm, EmptyForm
from . import productos_bp

@productos_bp.route('/')
@login_required
@requiere_rol('admin', 'cajero', 'vendedor', 'cocina', 'bodeguero')
def lista():
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    form = EmptyForm()
    return render_template('productos/lista.html', productos=productos, form=form)

@productos_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin', 'bodeguero')
@limiter.limit("10 per minute")
def crear():
    form = ProductoForm()

    if form.validate_on_submit():
        nombre = form.nombre.data
        categoria = form.categoria.data
        precio = form.precio.data
        stock_actual = form.stock_actual.data
        stock_minimo = form.stock_minimo.data
        unidad_medida = form.unidad_medida.data
        fecha_vencimiento = form.fecha_vencimiento.data

        producto = Producto(
            nombre=nombre, categoria=categoria, precio=precio,
            stock_actual=stock_actual, stock_minimo=stock_minimo,
            unidad_medida=unidad_medida, fecha_vencimiento=fecha_vencimiento
        )
        db.session.add(producto)
        db.session.commit()

        registrar_auditoria('CREAR_PRODUCTO', 'productos', f'Producto creado: {nombre} precio=${precio}')
        flash(f'Producto "{nombre}" creado exitosamente.', 'success')
        return redirect(url_for('productos.lista'))

    return render_template('productos/crear.html', form=form)

@productos_bp.route('/editar/<int:producto_id>', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin', 'bodeguero')
def editar(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    form = ProductoForm(obj=producto)

    if form.validate_on_submit():
        precio_anterior = producto.precio
        
        producto.nombre = form.nombre.data
        producto.categoria = form.categoria.data
        producto.precio = form.precio.data
        producto.stock_actual = form.stock_actual.data
        producto.stock_minimo = form.stock_minimo.data
        producto.unidad_medida = form.unidad_medida.data
        producto.fecha_vencimiento = form.fecha_vencimiento.data

        db.session.commit()

        if producto.precio != precio_anterior:
            registrar_auditoria('MODIFICAR_PRECIO', 'productos', f'Precio de {producto.nombre} cambió de ${precio_anterior} a ${producto.precio}')
        else:
            registrar_auditoria('EDITAR_PRODUCTO', 'productos', f'Producto editado: {producto.nombre}')

        flash(f'Producto "{producto.nombre}" actualizado correctamente.', 'success')
        return redirect(url_for('productos.lista'))

    return render_template('productos/editar.html', form=form, producto=producto)

@productos_bp.route('/eliminar/<int:producto_id>', methods=['POST'])
@login_required
@requiere_rol('admin')
def eliminar(producto_id):
    form = EmptyForm()
    if form.validate_on_submit():
        producto = Producto.query.get_or_404(producto_id)
        nombre = producto.nombre
        producto.activo = False
        db.session.commit()
        registrar_auditoria('ELIMINAR_PRODUCTO', 'productos', f'Producto eliminado: {nombre}')
        flash(f'Producto "{nombre}" eliminado.', 'warning')
    return redirect(url_for('productos.lista'))
