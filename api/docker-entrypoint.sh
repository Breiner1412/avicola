#!/bin/sh
set -e

echo "Esperando a la base de datos en ${DB_HOST}:${DB_PORT}..."
intentos=0
until python -c "
import os, socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect((os.environ.get('DB_HOST', 'db'), int(os.environ.get('DB_PORT', 3306))))
except OSError:
    sys.exit(1)
finally:
    s.close()
"; do
    intentos=$((intentos + 1))
    if [ "$intentos" -ge 60 ]; then
        echo "La base de datos no respondio. Se detiene el arranque."
        exit 1
    fi
    sleep 2
done

echo "Aplicando migraciones..."
alembic upgrade head

echo "Cargando datos iniciales..."
python -m app.semilla

echo "Iniciando la API..."
exec "$@"
