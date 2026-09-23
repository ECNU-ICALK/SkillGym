FROM wordpress:6.8.1-php8.2-apache

ENV DEBIAN_FRONTEND=noninteractive
ENV APACHE_RUN_USER=www-data
ENV APACHE_RUN_GROUP=www-data
ENV WP_URL=http://127.0.0.1
ENV WP_TITLE="Harbor Museum Printshop"
ENV WP_ADMIN_USER=admin
ENV WP_ADMIN_PASSWORD=AdminPass123!
ENV WP_ADMIN_EMAIL=admin@printshop.local
ENV WP_DB_NAME=wordpress
ENV WP_DB_USER=wordpress
ENV WP_DB_PASSWORD=wordpress
ENV WP_DB_HOST=127.0.0.1
ENV WP_ROOT=/var/www/html
ENV WORKSPACE_ROOT=/app/workspace
ENV DATA_ROOT=/app/data

RUN apt-get update \
  && apt-get install -y --no-install-recommends mariadb-server mariadb-client rsync unzip curl jq python3 less nodejs npm ripgrep \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /usr/local/bin/wp https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
  && chmod +x /usr/local/bin/wp \
  && mkdir -p /opt/wp-plugins \
  && curl -fsSL -o /tmp/woocommerce.zip https://downloads.wordpress.org/plugin/woocommerce.latest-stable.zip \
  && unzip -q /tmp/woocommerce.zip -d /opt/wp-plugins \
  && rm -f /tmp/woocommerce.zip

COPY data /app/data
COPY workspace /app/workspace
COPY bootstrap /opt/bootstrap
COPY skills /opt/task-skills-src

RUN mkdir -p /app/workspace/output /logs/verifier /run/mysqld /var/lib/mysql /opt/bootstrap \
  && chmod +x /opt/bootstrap/*.sh /app/workspace/scripts/*.sh \
  && chown -R mysql:mysql /run/mysqld /var/lib/mysql \
  && /opt/bootstrap/install_task_skills.sh \
  && sha256sum /app/data/* > /opt/printshop-data.sha256

ENTRYPOINT ["/opt/bootstrap/entrypoint.sh"]
CMD ["/bin/bash"]
