import uuid
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='vendedor')
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Security fields for brute-force protection
    login_intentos = db.Column(db.Integer, default=0, nullable=False)
    bloqueado_hasta = db.Column(db.DateTime, nullable=True)

    ventas = db.relationship('Venta', backref='cajero', lazy='dynamic',
                             foreign_keys='Venta.usuario_id')
    movimientos = db.relationship('MovimientoInventario', backref='responsable',
                                  lazy='dynamic', foreign_keys='MovimientoInventario.usuario_id')
    cierres = db.relationship('CierreCaja', backref='cajero_resp', lazy='dynamic',
                              foreign_keys='CierreCaja.cajero_id')
    auditorias = db.relationship('Auditoria', backref='usuario_resp', lazy='dynamic',
                                 foreign_keys='Auditoria.usuario_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        if self.bloqueado_hasta and self.bloqueado_hasta > datetime.utcnow():
            return True
        return False

    def __repr__(self):
        return f'<Usuario {self.nombre} [{self.rol}]>'


class Producto(db.Model):
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    precio = db.Column(db.Float, nullable=False, default=0.0)
    stock_actual = db.Column(db.Float, nullable=False, default=0.0)
    stock_minimo = db.Column(db.Float, nullable=False, default=0.0)
    unidad_medida = db.Column(db.String(30), default='unidad')
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    activo = db.Column(db.Boolean, default=True)

    detalles_venta = db.relationship('DetalleVenta', backref='producto', lazy='dynamic')
    movimientos = db.relationship('MovimientoInventario', backref='producto', lazy='dynamic')
    combos_como_insumo = db.relationship('InsumoCombo',
                                         foreign_keys='InsumoCombo.producto_insumo_id',
                                         backref='insumo', lazy='dynamic')
    combos_como_combo = db.relationship('InsumoCombo',
                                        foreign_keys='InsumoCombo.producto_combo_id',
                                        backref='combo_padre', lazy='dynamic')

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo

    @property
    def proximo_vencer(self):
        if self.fecha_vencimiento:
            from datetime import date, timedelta
            return self.fecha_vencimiento <= (date.today() + timedelta(days=7))
        return False

    def __repr__(self):
        return f'<Producto {self.nombre}>'


class Venta(db.Model):
    __tablename__ = 'ventas'

    id = db.Column(db.Integer, primary_key=True)
    numero_transaccion = db.Column(db.String(36), unique=True, nullable=False,
                                   default=lambda: str(uuid.uuid4()))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    metodo_pago = db.Column(db.String(20), nullable=False, default='efectivo')
    estado = db.Column(db.String(20), nullable=False, default='completada')
    total = db.Column(db.Float, nullable=False, default=0.0)

    detalles = db.relationship('DetalleVenta', backref='venta', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Venta {self.numero_transaccion} ${self.total}>'


class DetalleVenta(db.Model):
    __tablename__ = 'detalles_venta'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False, default=1.0)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<DetalleVenta {self.cantidad}x producto_id={self.producto_id}>'


class MovimientoInventario(db.Model):
    __tablename__ = 'movimientos_inventario'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'entrada' o 'salida'
    cantidad = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(200), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Movimiento {self.tipo} {self.cantidad} producto_id={self.producto_id}>'


class CierreCaja(db.Model):
    __tablename__ = 'cierres_caja'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    cajero_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    total_ventas_sistema = db.Column(db.Float, nullable=False, default=0.0)
    total_efectivo_real = db.Column(db.Float, nullable=False, default=0.0)
    diferencia = db.Column(db.Float, nullable=False, default=0.0)
    observaciones = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='CUADRADO')

    def __repr__(self):
        return f'<CierreCaja {self.fecha} {self.estado}>'


class Promocion(db.Model):
    __tablename__ = 'promociones'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='descuento')  # descuento/combo
    valor = db.Column(db.Float, nullable=False, default=0.0)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fin = db.Column(db.Time, nullable=True)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Promocion {self.nombre} {self.valor}%>'


class InsumoCombo(db.Model):
    __tablename__ = 'insumos_combo'

    id = db.Column(db.Integer, primary_key=True)
    producto_combo_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    producto_insumo_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad_necesaria = db.Column(db.Float, nullable=False, default=1.0)

    def __repr__(self):
        return f'<InsumoCombo combo={self.producto_combo_id} insumo={self.producto_insumo_id}>'


class Auditoria(db.Model):
    __tablename__ = 'auditoria'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    accion = db.Column(db.String(50), nullable=False)
    modulo = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Auditoria {self.accion} {self.modulo}>'
