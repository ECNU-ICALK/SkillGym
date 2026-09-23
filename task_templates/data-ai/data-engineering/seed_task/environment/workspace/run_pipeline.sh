#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLICKHOUSE_SERVER_NAME="harbor-task"
CLICKHOUSE_PROJECT_DIR="$ROOT_DIR"
CLICKHOUSE_USER_FILES_DIR="$CLICKHOUSE_PROJECT_DIR/.clickhouse/servers/$CLICKHOUSE_SERVER_NAME/data/user_files/nyc_tlc_task"
CLICKHOUSE_HTTP_PORT="8123"
CLICKHOUSE_TCP_PORT="9000"
TASK_BIN_DIR="$ROOT_DIR/.bin"

install_clickhousectl() {
  apt-get update
  apt-get install -y --no-install-recommends ca-certificates curl
  curl -fsSL https://clickhouse.com/cli | sh
}

install_clickhouse_binary() {
  cd "$CLICKHOUSE_PROJECT_DIR"
  clickhousectl local use stable >/dev/null
  CLICKHOUSE_BINARY_PATH="$(
    clickhousectl local which --json \
      | python3 -c "import json,sys; print(json.load(sys.stdin)['binary_path'])"
  )"
}

install_clickhouse_wrappers() {
  mkdir -p "$TASK_BIN_DIR"
  cat > "$TASK_BIN_DIR/clickhouse-client" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$CLICKHOUSE_BINARY_PATH" client --host 127.0.0.1 --port "$CLICKHOUSE_TCP_PORT" "\$@"
EOF
  chmod 0755 "$TASK_BIN_DIR/clickhouse-client"
}

start_clickhouse_server() {
  cd "$CLICKHOUSE_PROJECT_DIR"
  clickhousectl local init >/dev/null 2>&1 || true
  clickhousectl local server stop "$CLICKHOUSE_SERVER_NAME" >/dev/null 2>&1 || true
  clickhousectl local server remove "$CLICKHOUSE_SERVER_NAME" >/dev/null 2>&1 || true
  pkill -f "clickhouse server -- --path=" >/dev/null 2>&1 || true
  clickhousectl local server start \
    --name "$CLICKHOUSE_SERVER_NAME" \
    -v stable \
    --http-port "$CLICKHOUSE_HTTP_PORT" \
    --tcp-port "$CLICKHOUSE_TCP_PORT" \
    >/tmp/clickhouse-local-start.log 2>&1

  for _ in $(seq 1 60); do
    if clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "ClickHouse server did not become ready in time" >&2
  sed -n '1,200p' /tmp/clickhouse-local-start.log >&2 || true
  return 1
}

export PATH="$HOME/.local/bin:$TASK_BIN_DIR:$PATH"

if ! command -v clickhousectl >/dev/null 2>&1; then
  install_clickhousectl
  export PATH="$HOME/.local/bin:$TASK_BIN_DIR:$PATH"
fi

install_clickhouse_binary
install_clickhouse_wrappers
start_clickhouse_server

mkdir -p "$ROOT_DIR/output"
mkdir -p "$CLICKHOUSE_USER_FILES_DIR"

cp "$ROOT_DIR/data/taxi_zone_lookup.csv" "$CLICKHOUSE_USER_FILES_DIR/"
cp "$ROOT_DIR/data/yellow_tripdata_2023-01.parquet" "$CLICKHOUSE_USER_FILES_DIR/"
cp "$ROOT_DIR/data/yellow_tripdata_2023-02.parquet" "$CLICKHOUSE_USER_FILES_DIR/"
chmod 644 "$CLICKHOUSE_USER_FILES_DIR"/*

clickhouse-client --query "SELECT 1" >/dev/null

clickhouse-client --queries-file "$ROOT_DIR/sql/00_init.sql"
bash "$ROOT_DIR/pipeline/load_data.sh"
clickhouse-client --queries-file "$ROOT_DIR/sql/10_build_clean_trips.sql"
clickhouse-client --queries-file "$ROOT_DIR/sql/20_build_daily_borough_metrics.sql"
clickhouse-client --queries-file "$ROOT_DIR/sql/30_build_top_zone_routes.sql"
bash "$ROOT_DIR/pipeline/write_summary.sh"
