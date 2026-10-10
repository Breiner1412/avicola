#!/bin/sh
# Restaura un respaldo hecho con scripts/respaldo.sh. BORRA los datos actuales de la base.
#
# Uso, desde la raiz del proyecto:
#   sh scripts/restaurar.sh /var/backups/avicola/avicola_2026-10-09_0315.sql.gz --confirmo
#
# Detiene la API, vuelve a crear la base, carga el respaldo y arranca la API de nuevo.
set -eu
cd "$(dirname "$0")/.."

ARCHIVO="${1:-}"
CONFIRMO="${2:-}"
ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

if [ -z "$ARCHIVO" ] || [ ! -s "$ARCHIVO" ]; then
    echo "Uso: sh scripts/restaurar.sh <respaldo.sql.gz> --confirmo"
    exit 1
fi
if [ "$CONFIRMO" != "--confirmo" ]; then
    echo "Esto borra los datos actuales de la base. Si estas seguro, agrega --confirmo"
    exit 1
fi
gzip -t "$ARCHIVO"
# Antes de borrar nada: un volcado completo termina con esta linea
if ! gunzip -c "$ARCHIVO" | tail -n 1 | grep -q "Dump completed"; then
    echo "El respaldo esta incompleto (no termina con 'Dump completed'): no se toca la base"
    exit 1
fi

dc() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Deteniendo la API"
dc stop api
echo "Creando la base de nuevo"
dc exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "
    DROP DATABASE IF EXISTS \`$MYSQL_DATABASE\`;
    CREATE DATABASE \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
echo "Cargando $ARCHIVO"
gunzip -c "$ARCHIVO" | dc exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE"'
dc start api
echo "Restaurado. Revisa: docker compose ps"
