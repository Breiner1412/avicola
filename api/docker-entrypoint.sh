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

# Las migraciones las corre el servicio "migrar" de docker-compose, el unico que tiene
# las credenciales del duenio del esquema; la API arranca con MIGRAR=false.
if [ "${MIGRAR:-true}" = "true" ]; then
    echo "Aplicando migraciones..."
    alembic upgrade head

    echo "Cargando datos iniciales..."
    python -m app.semilla
fi

echo "Iniciando..."
exec "$@"
