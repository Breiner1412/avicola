#!/bin/sh
set -e

# Espera a que la base de datos acepte conexiones
python - <<'PY'
import sys, time
from core.database import check_database_connection
for intento in range(60):
    if check_database_connection():
        sys.exit(0)
    print("Esperando a la base de datos...", flush=True)
    time.sleep(2)
print("La base de datos no respondió a tiempo", flush=True)
sys.exit(1)
PY

# Crea el superadmin inicial si se definieron ADMIN_EMAIL y ADMIN_PASSWORD
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    python -m scripts.crear_superadmin
fi

exec "$@"
