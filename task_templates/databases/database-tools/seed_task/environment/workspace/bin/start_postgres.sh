#!/usr/bin/env bash

set -euo pipefail

source /root/workspace/bin/common.sh

if [ -x /usr/lib/postgresql/16/bin/initdb ]; then
    PG_BIN_DIR=/usr/lib/postgresql/16/bin
elif [ -x /usr/lib/postgresql/17/bin/initdb ]; then
    PG_BIN_DIR=/usr/lib/postgresql/17/bin
else
    PG_BIN_DIR="$(dirname "$(find /usr/lib/postgresql -type f -name initdb | sort | tail -n 1)")"
fi

INITDB_BIN="$PG_BIN_DIR/initdb"
PG_CTL_BIN="$PG_BIN_DIR/pg_ctl"

if [ ! -x "$INITDB_BIN" ] || [ ! -x "$PG_CTL_BIN" ]; then
    echo "Could not locate initdb/pg_ctl under /usr/lib/postgresql" >&2
    exit 1
fi

mkdir -p "$PGHOST"
chown postgres:postgres "$PGHOST"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    rm -rf "$PGDATA"
    mkdir -p "$PGDATA"
    chown postgres:postgres "$PGDATA"
    runuser -u postgres -- "$INITDB_BIN" -D "$PGDATA" >/tmp/rapid-transit-initdb.log
fi

if ! runuser -u postgres -- "$PG_CTL_BIN" -D "$PGDATA" status >/dev/null 2>&1; then
    runuser -u postgres -- "$PG_CTL_BIN" \
        -D "$PGDATA" \
        -l "$PGLOG" \
        -o "-k $PGHOST -p $PGPORT -c listen_addresses='' -c unix_socket_permissions=0777 -c timezone=UTC" \
        start
fi

for _ in $(seq 1 30); do
    if psql_maintenance -Atqc "SELECT 1" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! db_exists; then
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$DB_NAME"
fi
