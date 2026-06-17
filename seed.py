import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.extensions import db
from app.models import Usuario, Producto, Promocion, InsumoCombo
from datetime import time, date

def seed():
    # Asume que ya corre dentro del app_context
    db.create_all()

    # ── USUARIOS ────────────────────────────────────────────
    usuarios_data = [
        ('Administrador SIGCAFE', 'admin@cafeteria.com', 'admin123M@', 'admin'),
        ('Cajero Principal', 'cajero1@cafeteria.com', 'cajero123C@', 'cajero'),
        ('Vendedor Uno', 'vendedor1@cafeteria.com', 'vendedor123V@', 'vendedor'),
        ('Cocina Principal', 'cocina1@cafeteria.com', 'cocina123K@', 'cocina'),
        ('Bodeguero Central', 'bodeguero1@cafeteria.com', 'bodega123B@', 'bodeguero'),
    ]

    for nombre, email, pwd, rol in usuarios_data:
        if not Usuario.query.filter_by(email=email).first():
            u = Usuario(nombre=nombre, email=email, rol=rol)
            u.set_password(pwd)
            db.session.add(u)
            print(f'  ✓ Usuario: {nombre} [{rol}]')

    db.session.commit()

    # ── PRODUCTOS ────────────────────────────────────────────
    productos_data = [
        ('Jugo de naranja',      'bebida',   1.50, 50,  10,  'unidad',  None),
        ('Empanada de morocho',  'snack',    0.75, 30,   5,  'unidad',  None),
        ('Almuerzo del dia',     'almuerzo', 3.00, 40,  10,  'porcion', None),
        ('Cafe americano',       'bebida',   1.00, 100, 20,  'unidad',  None),
        ('Sanduche mixto',       'snack',    1.25, 25,   5,  'unidad',  None),
        ('Agua sin gas',         'bebida',   0.50, 60,  15,  'unidad',  None),
        ('Torta de chocolate',   'postre',   1.75, 20,   5,  'unidad',  date(2026, 6, 20)),
        ('Combo estudiantil',    'combo',    2.50,  0,   0,  'combo',   None),
    ]

    for nombre, cat, precio, stock, minimo, unidad, venc in productos_data:
        if not Producto.query.filter_by(nombre=nombre).first():
            p = Producto(
                nombre=nombre, categoria=cat, precio=precio,
                stock_actual=stock, stock_minimo=minimo,
                unidad_medida=unidad, fecha_vencimiento=venc
            )
            db.session.add(p)
            print(f'  ✓ Producto: {nombre} (${precio})')

    db.session.commit()

    # ── INSUMOS COMBO ────────────────────────────────────────
    combo = Producto.query.filter_by(nombre='Combo estudiantil').first()
    almuerzo = Producto.query.filter_by(nombre='Almuerzo del dia').first()
    agua = Producto.query.filter_by(nombre='Agua sin gas').first()

    if combo and almuerzo and agua:
        if not InsumoCombo.query.filter_by(
                producto_combo_id=combo.id,
                producto_insumo_id=almuerzo.id).first():
            ic1 = InsumoCombo(
                producto_combo_id=combo.id,
                producto_insumo_id=almuerzo.id,
                cantidad_necesaria=1.0
            )
            ic2 = InsumoCombo(
                producto_combo_id=combo.id,
                producto_insumo_id=agua.id,
                cantidad_necesaria=1.0
            )
            db.session.add_all([ic1, ic2])
            print('  ✓ Insumos del Combo estudiantil configurados')

    # ── PROMOCIONES ──────────────────────────────────────────
    if not Promocion.query.filter_by(nombre='Descuento mediodia').first():
        promo = Promocion(
            nombre='Descuento mediodia',
            tipo='descuento',
            valor=10.0,
            hora_inicio=time(12, 0),
            hora_fin=time(14, 0),
            activo=True
        )
        db.session.add(promo)
        print('  ✓ Promocion: Descuento mediodia (10%)')

    db.session.commit()
    print('\n✅ Base de datos inicializada correctamente.')

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        seed()
