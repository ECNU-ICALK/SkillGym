#!/usr/bin/env bash

set -euo pipefail

export TASK_ROOT="${TASK_ROOT:-/root/workspace}"
export DATA_DIR="${TASK_DATA_DIR:-/root/data}"
export OUTPUT_DIR="${TASK_OUTPUT_DIR:-/root/output}"

export PGDATA="${PGDATA:-/tmp/sql-databases-pgdata}"
export PGHOST="${PGHOST:-/tmp/sql-databases-pg}"
export PGPORT="${PGPORT:-55433}"
export PGUSER="${PGUSER:-postgres}"
export DB_NAME="${DB_NAME:-airport_ops_task}"
export PGLOG="${PGLOG:-/tmp/sql-databases-postgres.log}"

psql_db() {
    psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" "$@"
}

psql_maintenance() {
    psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres "$@"
}

db_exists() {
    psql_maintenance -Atqc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q '^1$'
}
