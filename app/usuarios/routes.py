from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from ..models import Usuario
from ..extensions import db, limiter
from ..decorators import requiere_rol
from ..utils import registrar_auditoria
from ..forms import UsuarioForm, EmptyForm
from . import usuarios_bp

@usuarios_bp.route('/')
@login_required
@requiere_rol('admin')
def lista():
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    form = EmptyForm() # Para boton eliminar (CSRF)
    return render_template('usuarios/lista.html', usuarios=usuarios, form=form)

@usuarios_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin')
@limiter.limit("5 per minute")
def crear():
    form = UsuarioForm()
    
    if form.validate_on_submit():
        nombre = form.nombre.data
        email = form.email.data
        password = form.password.data
        rol = form.rol.data

        if not password:
            flash('La contraseña es obligatoria para nuevos usuarios.', 'danger')
            return render_template('usuarios/crear.html', form=form)

        if Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email.', 'danger')
            return render_template('usuarios/crear.html', form=form)

        usuario = Usuario(nombre=nombre, email=email, rol=rol)
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()

        registrar_auditoria('CREAR_USUARIO', 'usuarios', f'Usuario creado: {nombre} ({email}) rol={rol}')
        flash(f'Usuario {nombre} creado exitosamente.', 'success')
        return redirect(url_for('usuarios.lista'))

    return render_template('usuarios/crear.html', form=form)

@usuarios_bp.route('/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@requiere_rol('admin')
def editar(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    form = UsuarioForm(obj=usuario)

    if form.validate_on_submit():
        nombre = form.nombre.data
        email = form.email.data
        rol = form.rol.data
        activo = form.activo.data
        nueva_password = form.password.data

        existing = Usuario.query.filter(Usuario.email == email, Usuario.id != usuario_id).first()
        if existing:
            flash('Ya existe otro usuario con ese email.', 'danger')
            return render_template('usuarios/editar.html', form=form, usuario=usuario)

        usuario.nombre = nombre
        usuario.email = email
        usuario.rol = rol
        usuario.activo = activo

        if nueva_password:
            usuario.set_password(nueva_password)

        db.session.commit()
        registrar_auditoria('EDITAR_USUARIO', 'usuarios', f'Usuario editado: {nombre} ({email}) rol={rol}')
        flash(f'Usuario {nombre} actualizado correctamente.', 'success')
        return redirect(url_for('usuarios.lista'))

    return render_template('usuarios/editar.html', form=form, usuario=usuario)

@usuarios_bp.route('/eliminar/<int:usuario_id>', methods=['POST'])
@login_required
@requiere_rol('admin')
def eliminar(usuario_id):
    form = EmptyForm()
    if form.validate_on_submit():
        usuario = Usuario.query.get_or_404(usuario_id)
        if usuario.id == current_user.id:
            flash('No puedes desactivar tu propio usuario.', 'danger')
            return redirect(url_for('usuarios.lista'))
            
        nombre = usuario.nombre
        usuario.activo = False
        db.session.commit()
        registrar_auditoria('DESACTIVAR_USUARIO', 'usuarios', f'Usuario desactivado: {nombre}')
        flash(f'Usuario {nombre} desactivado.', 'warning')
    return redirect(url_for('usuarios.lista'))
