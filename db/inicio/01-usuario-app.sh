#!/bin/sh
# Crea (o actualiza) el usuario con el que trabaja la aplicacion.
#
# Solo puede leer y escribir datos: no crea ni quita tablas ni triggers, asi que
# no puede saltarse los triggers que dejan el registro de cambios de solo insercion.
# Las migraciones usan el usuario duenio del esquema (MYSQL_USER).
#
# MySQL lo ejecuta solo la primera vez (con el volumen vacio). En una base que ya
# existe, correrlo una vez a mano:
#   docker compose exec db sh /docker-entrypoint-initdb.d/01-usuario-app.sh
set -eu

: "${DB_APP_USER:?falta DB_APP_USER}"
: "${DB_APP_PASSWORD:?falta DB_APP_PASSWORD}"
: "${MYSQL_DATABASE:?falta MYSQL_DATABASE}"

MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot <<SQL
CREATE USER IF NOT EXISTS '${DB_APP_USER}'@'%' IDENTIFIED BY '${DB_APP_PASSWORD}';
ALTER USER '${DB_APP_USER}'@'%' IDENTIFIED BY '${DB_APP_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`${MYSQL_DATABASE}\`.* TO '${DB_APP_USER}'@'%';
FLUSH PRIVILEGES;
SQL
echo "Usuario de la aplicacion listo: ${DB_APP_USER}"
