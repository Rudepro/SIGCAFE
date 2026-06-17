#!/bin/bash
# Script de backup de la base de datos SQLite
BACKUP_DIR="/app/data/backups"
DB_FILE="/app/data/sigcafe.db"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/sigcafe_backup_$TIMESTAMP.db"

if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "Backup creado: $BACKUP_FILE"
    # Mantener solo los últimos 7 backups
    ls -t "$BACKUP_DIR"/sigcafe_backup_*.db | tail -n +8 | xargs -r rm --
else
    echo "Base de datos no encontrada para respaldar."
fi
