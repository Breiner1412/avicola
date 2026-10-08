#!/bin/sh
# Crea el volcado base de la demo publica.
#
# Deja la base de la demo vacia, aplica las migraciones, simula los ultimos meses
# de trabajo con app.demo y guarda el resultado en DEMO_BASE. El reinicio nocturno
# (reiniciar.sh) vuelve a cargar ese volcado.
#
# Las fechas de la demo terminan el dia en que se crea el volcado: conviene
# regenerarlo cada semana (ver README, "Demo publica").
#
# Uso, desde la raiz del proyecto:
#   sh scripts/demo/crear_base.sh [dias]      (por defecto 180)
set -eu
cd "$(dirname "$0")/../.."
. scripts/demo/comun.sh

DIAS="${1:-180}"
exigir_demo
bloquear

log "Creando la base de la demo con $DIAS dias de datos"
dc stop api
recrear_base
dc start api          # el arranque aplica migraciones y datos iniciales
esperar_api

log "Simulando el trabajo de la granja (puede tardar unos minutos)"
dc exec -T api python -m app.demo --dias "$DIAS"

mkdir -p "$(dirname "$DEMO_BASE")"
log "Guardando el volcado en $DEMO_BASE"
dc exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot \
    --single-transaction --quick --routines --triggers --hex-blob \
    --default-character-set=utf8mb4 --set-gtid-purged=OFF "$MYSQL_DATABASE"' \
    | gzip -9 > "$DEMO_BASE.tmp"
mv "$DEMO_BASE.tmp" "$DEMO_BASE"
vaciar_cache
log "Listo: $(du -h "$DEMO_BASE" | cut -f1)"
