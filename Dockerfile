FROM python:3.11-slim

# No correr como root: crear usuario y grupo
RUN groupadd -r sigcafe && useradd -r -g sigcafe sigcafe

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y dependencias
COPY requirements.txt .

# Instalar dependencias sin caché para reducir el tamaño de la imagen
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear carpetas necesarias y establecer permisos restrictivos
RUN mkdir -p /app/data /app/logs && \
    chown -R sigcafe:sigcafe /app && \
    chmod 700 /app/data && \
    chmod 700 /app/logs

# Ejecutar seed (esto debe hacerse antes de cambiar de usuario, o después, pero los archivos DB los poseerá sigcafe)
USER sigcafe

# Comando de inicio
EXPOSE 5000
CMD ["python", "run.py"]
