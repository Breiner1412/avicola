#!/bin/sh
# Respaldo de la base de datos de Avicola con mysqldump, desde la VM.
#
# Guarda un .sql.gz con fecha y hora, comprueba que el archivo este sano y borra
# los respaldos de mas de DIAS_RETENCION dias. Pensado para el cron del host.
#
# Uso, desde la raiz del proyecto:
#   sh scripts/respaldo.sh
#
# Variables opcionales:
#   RESPALDOS       carpeta destino (por defecto /var/backups/avicola)
#   DIAS_RETENCION  cuantos dias se guardan (por defecto 14)
#   ENV_FILE        archivo de entorno (por defecto .env)
#   COMPOSE_FILE    archivo de Docker Compose (por defecto docker-compose.yml)
set -eu
cd "$(dirname "$0")/.."

RESPALDOS="${RESPALDOS:-/var/backups/avicola}"
DIAS_RETENCION="${DIAS_RETENCION:-14}"
ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*"
}

mkdir -p "$RESPALDOS"
chmod 700 "$RESPALDOS"
base=$(sed -n 's/^DB_NAME=//p' "$ENV_FILE" | tail -n 1 | tr -d '"\r')
destino="$RESPALDOS/${base:-avicola}_$(date +%Y-%m-%d_%H%M).sql.gz"

log "Respaldando ${base:-avicola} en $destino"
# --single-transaction: copia consistente sin bloquear la app (InnoDB)
# --routines --triggers --events: incluye los triggers del registro de cambios
# La clave de root la lee el shell dentro del contenedor (no queda en el host)
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot \
        --single-transaction --quick --routines --triggers --events --hex-blob \
        --default-character-set=utf8mb4 --set-gtid-purged=OFF --no-tablespaces \
        "$MYSQL_DATABASE"' \
    | gzip -9 > "$destino.tmp"

# Un volcado completo termina con esta linea; si no esta, algo fallo a la mitad
if ! gzip -t "$destino.tmp" || ! gunzip -c "$destino.tmp" | tail -n 1 | grep -q "Dump completed"; then
    rm -f "$destino.tmp"
    log "El respaldo quedo incompleto y se descarto"
    exit 1
fi
mv "$destino.tmp" "$destino"
chmod 600 "$destino"
log "Listo: $(du -h "$destino" | cut -f1)"

find "$RESPALDOS" -name '*.sql.gz' -type f -mtime +"$DIAS_RETENCION" -print -delete | sed 's/^/Borrado por antiguo: /'
