#!/bin/bash
set -euo pipefail

echo "[start_stack] booting mariadb"
/opt/bootstrap/start_mariadb.sh
echo "[start_stack] configuring wordpress"
/opt/bootstrap/configure_wordpress.sh

if ! pgrep -f "php -S 127.0.0.1:80 /opt/bootstrap/php-router.php" >/dev/null 2>&1; then
  echo "[start_stack] starting php server"
  php -S 127.0.0.1:80 -t "${WP_ROOT:-/var/www/html}" /opt/bootstrap/php-router.php >/tmp/php-server.log 2>&1 &
fi

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1/wp-json/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS http://127.0.0.1/wp-json/ >/dev/null 2>&1 || {
  echo "[start_stack] wp-json did not become ready" >&2
  cat /tmp/php-server.log >&2 || true
  exit 1
}

echo "[start_stack] stack ready"
