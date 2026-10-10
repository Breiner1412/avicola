#!/bin/sh
# Reinicio nocturno de la demo publica: vuelve a dejar los datos como en el
# volcado base (creado con crear_base.sh). Pensado para el cron del host.
#
# Uso, desde la raiz del proyecto:
#   sh scripts/demo/reiniciar.sh
set -eu
cd "$(dirname "$0")/../.."
. scripts/demo/comun.sh

exigir_demo
bloquear
[ -s "$DEMO_BASE" ] || { log "No existe el volcado base $DEMO_BASE: corre primero crear_base.sh"; exit 1; }
gzip -t "$DEMO_BASE" || { log "El volcado base $DEMO_BASE esta danado"; exit 1; }

log "Reiniciando la demo"
dc stop api
recrear_base
log "Cargando $DEMO_BASE"
gunzip -c "$DEMO_BASE" | dc exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE"'
vaciar_cache
dc run --rm migrar    # por si el codigo trae migraciones nuevas desde que se hizo el volcado
dc start api
esperar_api
log "Demo reiniciada"
