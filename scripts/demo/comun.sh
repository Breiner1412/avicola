# Funciones comunes de los scripts de la demo. Se cargan con ". scripts/demo/comun.sh"
# desde la raiz del proyecto.
#
# Variables opcionales:
#   ENV_FILE      archivo de entorno (por defecto .env)
#   COMPOSE_FILE  archivo de Docker Compose (por defecto el del proyecto)
#   DEMO_BASE     donde queda el volcado base (por defecto demo/base_demo.sql.gz)

ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DEMO_BASE="${DEMO_BASE:-demo/base_demo.sql.gz}"

dc() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*"
}

valor_env() {
    # Lee una variable del archivo de entorno sin ejecutarlo
    sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1 | tr -d '"\r'
}

exigir_demo() {
    [ -f "$ENV_FILE" ] || { log "No existe $ENV_FILE"; exit 1; }
    demo=$(valor_env DEMO | tr '[:upper:]' '[:lower:]')
    base=$(valor_env DB_NAME)
    if [ "$demo" != "true" ]; then
        log "DEMO no es true en $ENV_FILE: este script solo se usa con la demo"; exit 1
    fi
    case "$base" in
        *_demo) ;;
        *) log "DB_NAME ($base) no termina en _demo: no se toca esa base"; exit 1 ;;
    esac
}

bloquear() {
    # Evita que dos reinicios corran a la vez
    if ! command -v flock >/dev/null 2>&1; then
        log "Aviso: no hay flock, se sigue sin bloqueo"; return
    fi
    exec 9>"${TMPDIR:-/tmp}/avicola-demo.lock"
    flock -n 9 || { log "Ya hay otro proceso de la demo en marcha"; exit 1; }
}

recrear_base() {
    log "Borrando y creando de nuevo la base $(valor_env DB_NAME)"
    dc exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "
        DROP DATABASE IF EXISTS \`$MYSQL_DATABASE\`;
        CREATE DATABASE \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
}

esperar_api() {
    log "Esperando a que la API responda"
    intentos=0
    until dc exec -T api curl -fsS http://127.0.0.1:8000/api/v1/salud >/dev/null 2>&1; do
        intentos=$((intentos + 1))
        if [ "$intentos" -ge 90 ]; then log "La API no respondio"; exit 1; fi
        sleep 2
    done
}

vaciar_cache() {
    # Limites de intentos y demas: que nadie quede bloqueado del dia anterior
    dc exec -T cache sh -c 'redis-cli FLUSHALL' >/dev/null
}
