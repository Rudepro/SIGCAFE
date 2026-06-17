from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from ..models import Promocion
from ..extensions import db, limiter
from ..decorators import requiere_rol
from ..utils import registrar_auditoria
from ..forms import PromocionForm, EmptyForm
from . import promociones_bp

@promociones_bp.route('/')
@login_required
@requiere_rol('admin', 'cajero', 'vendedor')
def lista():
    promociones = Promocion.query.order_by(Promocion.nombre).all()
    form = EmptyForm()
    return render_template('promociones/lista.html', promociones=promociones, form=form)

@promociones_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin')
@limiter.limit("5 per minute")
def crear():
    form = PromocionForm()

    if form.validate_on_submit():
        nombre = form.nombre.data
        tipo = form.tipo.data
        valor = form.valor.data
        hora_inicio = form.hora_inicio.data
        hora_fin = form.hora_fin.data

        if (hora_inicio and not hora_fin) or (hora_fin and not hora_inicio):
            flash('Debe definir tanto hora de inicio como hora de fin.', 'warning')
            return render_template('promociones/crear.html', form=form)

        promocion = Promocion(
            nombre=nombre, tipo=tipo, valor=valor,
            hora_inicio=hora_inicio, hora_fin=hora_fin
        )
        db.session.add(promocion)
        db.session.commit()

        registrar_auditoria('CREAR_PROMOCION', 'promociones', f'Promoción creada: {nombre} ({tipo})')
        flash(f'Promoción "{nombre}" creada.', 'success')
        return redirect(url_for('promociones.lista'))

    return render_template('promociones/crear.html', form=form)

@promociones_bp.route('/toggle/<int:promo_id>', methods=['POST'])
@login_required
@requiere_rol('admin')
def toggle(promo_id):
    form = EmptyForm()
    if form.validate_on_submit():
        promo = Promocion.query.get_or_404(promo_id)
        promo.activo = not promo.activo
        db.session.commit()
        estado = "activada" if promo.activo else "desactivada"
        registrar_auditoria('TOGGLE_PROMOCION', 'promociones', f'Promoción {promo.nombre} {estado}')
        flash(f'Promoción "{promo.nombre}" {estado}.', 'info')
    return redirect(url_for('promociones.lista'))

@promociones_bp.route('/eliminar/<int:promo_id>', methods=['POST'])
@login_required
@requiere_rol('admin')
def eliminar(promo_id):
    form = EmptyForm()
    if form.validate_on_submit():
        promo = Promocion.query.get_or_404(promo_id)
        nombre = promo.nombre
        db.session.delete(promo)
        db.session.commit()
        registrar_auditoria('ELIMINAR_PROMOCION', 'promociones', f'Promoción eliminada: {nombre}')
        flash(f'Promoción "{nombre}" eliminada.', 'warning')
    return redirect(url_for('promociones.lista'))
