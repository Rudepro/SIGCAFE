import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from seed import seed
from app.extensions import db
from app.models import Usuario

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    with app.app_context():
        # Inicializar BD y seed automáticamento si está vacía
        try:
            if not Usuario.query.first():
                print("Base de datos vacía, ejecutando seed.py...")
                seed()
        except Exception as e:
            print("Creando base de datos y ejecutando seed.py...")
            db.create_all()
            seed()

    app.run(host='0.0.0.0', port=5000, debug=False)
