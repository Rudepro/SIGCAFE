import bleach
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, FloatField, SelectField, DateField, TimeField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email, NumberRange, Regexp, Optional, ValidationError

# Constantes para selectores
ROLES = [('admin', 'Admin'), ('cajero', 'Cajero'), ('vendedor', 'Vendedor'), ('cocina', 'Cocina'), ('bodeguero', 'Bodeguero')]
CATEGORIAS = [(c, c.capitalize()) for c in ['desayuno', 'almuerzo', 'snack', 'bebida', 'postre', 'empaquetado', 'combo', 'otro']]
UNIDADES = [(u, u.capitalize()) for u in ['unidad', 'porcion', 'litro', 'kilogramo', 'gramo', 'docena']]
TIPOS_MOVIMIENTO = [('entrada', 'Entrada'), ('salida', 'Salida')]
METODOS_PAGO = [(m, m.capitalize()) for m in ['efectivo', 'tarjeta', 'transferencia', 'credito']]
TIPOS_PROMOCION = [('descuento', 'Descuento'), ('combo', 'Combo')]

def sanitize_html(form, field):
    if field.data:
        field.data = bleach.clean(field.data.strip())

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Contraseña', validators=[DataRequired()])

class UsuarioForm(FlaskForm):
    nombre = StringField('Nombre completo', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Contraseña', validators=[
        Optional(), 
        Length(min=8),
        Regexp(r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', 
               message="La contraseña debe tener al menos 8 caracteres, una mayúscula, un número y un carácter especial (@$!%*?&)")
    ])
    rol = SelectField('Rol', choices=ROLES, validators=[DataRequired()])
    activo = BooleanField('Activo', default=True)

    def validate_nombre(self, field):
        sanitize_html(self, field)

class ProductoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=150)])
    categoria = SelectField('Categoría', choices=CATEGORIAS, validators=[DataRequired()])
    precio = FloatField('Precio ($)', validators=[DataRequired(), NumberRange(min=0.01, max=99999)])
    stock_actual = FloatField('Stock Actual', default=0.0, validators=[NumberRange(min=0, max=99999)])
    stock_minimo = FloatField('Stock Mínimo', default=0.0, validators=[NumberRange(min=0, max=99999)])
    unidad_medida = SelectField('Unidad', choices=UNIDADES, validators=[DataRequired()])
    fecha_vencimiento = DateField('Fecha de Vencimiento', format='%Y-%m-%d', validators=[Optional()])

    def validate_nombre(self, field):
        sanitize_html(self, field)

class MovimientoInventarioForm(FlaskForm):
    producto_id = HiddenField('Producto ID', validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=TIPOS_MOVIMIENTO, validators=[DataRequired()])
    cantidad = FloatField('Cantidad', validators=[DataRequired(), NumberRange(min=0.01, max=99999)])
    motivo = StringField('Motivo', validators=[DataRequired(), Length(max=200)])

    def validate_motivo(self, field):
        sanitize_html(self, field)

class CierreCajaForm(FlaskForm):
    total_efectivo_real = FloatField('Total efectivo', default=0.0, validators=[NumberRange(min=0, max=999999)])
    observaciones = TextAreaField('Observaciones', validators=[Optional(), Length(max=1000)])

    def validate_observaciones(self, field):
        sanitize_html(self, field)

class PromocionForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    tipo = SelectField('Tipo', choices=TIPOS_PROMOCION, validators=[DataRequired()])
    valor = FloatField('Valor', validators=[DataRequired(), NumberRange(min=0.01, max=99999)])
    hora_inicio = TimeField('Hora Inicio', validators=[Optional()])
    hora_fin = TimeField('Hora Fin', validators=[Optional()])

    def validate_nombre(self, field):
        sanitize_html(self, field)

class VentaForm(FlaskForm):
    metodo_pago = SelectField('Método de Pago', choices=METODOS_PAGO, validators=[DataRequired()])
    items = HiddenField('Items', validators=[DataRequired()]) # JSON string validated in route

class EmptyForm(FlaskForm):
    # Used for POST requests that only need CSRF (like deletes)
    pass
