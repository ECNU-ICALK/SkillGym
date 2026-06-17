#!/bin/bash
set -euo pipefail

: "${WP_DB_NAME:=wordpress}"
: "${WP_DB_USER:=wordpress}"
: "${WP_DB_PASSWORD:=wordpress}"

if [ ! -d /var/lib/mysql/mysql ]; then
  mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/tmp/mariadb-install.log 2>&1
fi

if ! pgrep -x mariadbd >/dev/null 2>&1; then
  mkdir -p /run/mysqld
  chown mysql:mysql /run/mysqld /var/lib/mysql
  mariadbd --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 >/tmp/mariadb.log 2>&1 &
fi

for _ in $(seq 1 60); do
  if mysqladmin ping --host=127.0.0.1 --silent >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

mysqladmin ping --host=127.0.0.1 --silent >/dev/null 2>&1 || {
  cat /tmp/mariadb.log >&2 || true
  exit 1
}

mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS \`${WP_DB_NAME}\`;
CREATE USER IF NOT EXISTS '${WP_DB_USER}'@'localhost' IDENTIFIED BY '${WP_DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${WP_DB_USER}'@'127.0.0.1' IDENTIFIED BY '${WP_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${WP_DB_NAME}\`.* TO '${WP_DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${WP_DB_NAME}\`.* TO '${WP_DB_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL
