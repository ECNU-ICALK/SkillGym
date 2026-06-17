#!/bin/bash
set -euo pipefail

: "${WP_URL:=http://127.0.0.1}"
: "${WP_TITLE:=Harbor Museum Printshop}"
: "${WP_ADMIN_USER:=admin}"
: "${WP_ADMIN_PASSWORD:=AdminPass123!}"
: "${WP_ADMIN_EMAIL:=admin@printshop.local}"
: "${WP_DB_NAME:=wordpress}"
: "${WP_DB_USER:=wordpress}"
: "${WP_DB_PASSWORD:=wordpress}"
: "${WP_DB_HOST:=127.0.0.1}"
: "${WP_ROOT:=/var/www/html}"
: "${WORKSPACE_ROOT:=/app/workspace}"

mkdir -p "${WP_ROOT}"

if [ ! -f "${WP_ROOT}/wp-load.php" ]; then
  rsync -a /usr/src/wordpress/ "${WP_ROOT}/"
fi

if [ ! -f "${WP_ROOT}/wp-config.php" ]; then
  wp config create \
    --allow-root \
    --path="${WP_ROOT}" \
    --dbname="${WP_DB_NAME}" \
    --dbuser="${WP_DB_USER}" \
    --dbpass="${WP_DB_PASSWORD}" \
    --dbhost="${WP_DB_HOST}" \
    --skip-check \
    --extra-php <<PHP
define('FS_METHOD', 'direct');
define('WP_DEBUG', false);
define('WP_HOME', '${WP_URL}');
define('WP_SITEURL', '${WP_URL}');
PHP
fi

if ! wp core is-installed --allow-root --path="${WP_ROOT}" >/dev/null 2>&1; then
  wp core install \
    --allow-root \
    --path="${WP_ROOT}" \
    --url="${WP_URL}" \
    --title="${WP_TITLE}" \
    --admin_user="${WP_ADMIN_USER}" \
    --admin_password="${WP_ADMIN_PASSWORD}" \
    --admin_email="${WP_ADMIN_EMAIL}"
fi

mkdir -p "${WP_ROOT}/wp-content/plugins"
if [ ! -d "${WP_ROOT}/wp-content/plugins/woocommerce" ]; then
  cp -R /opt/wp-plugins/woocommerce "${WP_ROOT}/wp-content/plugins/woocommerce"
fi

rm -rf "${WP_ROOT}/wp-content/plugins/harbor-printshop"
ln -s "${WORKSPACE_ROOT}/plugin" "${WP_ROOT}/wp-content/plugins/harbor-printshop"

wp plugin activate woocommerce --allow-root --path="${WP_ROOT}" >/dev/null 2>&1 || true
wp plugin activate harbor-printshop --allow-root --path="${WP_ROOT}" >/dev/null 2>&1 || true
wp rewrite structure '/%postname%/' --hard --allow-root --path="${WP_ROOT}" >/dev/null 2>&1 || true
wp option update blog_public 0 --allow-root --path="${WP_ROOT}" >/dev/null 2>&1 || true
