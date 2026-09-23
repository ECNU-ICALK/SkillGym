from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest


TASK_ROOT = Path("/app") if Path("/app/workspace").exists() else Path("/home/lenovo/skill/Harbor/skill_moban/development/backend/template_new/environment")
WORKSPACE_ROOT = TASK_ROOT / "workspace"
DATA_ROOT = WORKSPACE_ROOT / "data"
STATE_ROOT = WORKSPACE_ROOT / "state"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def static_data_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(DATA_ROOT.iterdir()):
        if path.name == "refund_requests.json":
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def reset_runtime_state(workspace_root: Path = WORKSPACE_ROOT, data_dir: Path | None = None, state_dir: Path | None = None) -> None:
    env = os.environ.copy()
    if data_dir is not None:
        env["DATA_DIR"] = str(data_dir)
    if state_dir is not None:
        env["STATE_DIR"] = str(state_dir)
    subprocess.run(
        ["node", "scripts/reset_runtime_state.js"],
        cwd=workspace_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
) -> tuple[int, dict[str, str], dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    if api_key is not None:
        request_headers["X-Partner-Key"] = api_key
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(
        urllib.parse.urljoin(base_url, path),
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, dict(resp.headers), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), json.loads(exc.read().decode("utf-8"))


def attach_customer(order: dict, customers_by_id: dict[str, dict]) -> dict:
    customer = customers_by_id[order["customer_id"]]
    return {
        **order,
        "customer": {
            "id": customer["id"],
            "name": customer["name"],
            "email": customer["email"],
            "country": customer["default_address"]["country_code"],
        },
    }


def expected_order_slice(
    data_dir: Path,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    customer_country: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    sort: str = "-created_at",
) -> tuple[list[dict], int]:
    orders = read_json(data_dir / "orders_snapshot.json")
    customers = read_json(data_dir / "customers_snapshot.json")
    customers_by_id = {row["id"]: row for row in customers}
    rows = [attach_customer(order, customers_by_id) for order in orders]
    if status is not None:
        rows = [row for row in rows if row["financial_status"] == status]
    if customer_country is not None:
        rows = [row for row in rows if row["customer"]["country"] == customer_country]
    if created_from is not None:
        rows = [row for row in rows if row["created_at"] >= created_from]
    if created_to is not None:
        rows = [row for row in rows if row["created_at"] <= created_to]

    reverse = sort.startswith("-")
    key_name = sort[1:] if reverse else sort
    rows.sort(key=lambda row: (row[key_name], row["id"]), reverse=reverse)
    total_items = len(rows)
    start = max(0, (page - 1) * page_size)
    return rows[start : start + page_size], total_items


def runtime_refund_count(state_dir: Path = STATE_ROOT) -> int:
    return len(read_json(state_dir / "runtime_state.json")["refunds"])


@contextmanager
def running_server(
    *,
    workspace_root: Path = WORKSPACE_ROOT,
    data_dir: Path = DATA_ROOT,
    state_dir: Path = STATE_ROOT,
) -> str:
    reset_runtime_state(workspace_root=workspace_root, data_dir=data_dir, state_dir=state_dir)
    port = _free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["DATA_DIR"] = str(data_dir)
    env["STATE_DIR"] = str(state_dir)
    process = subprocess.Popen(
        ["node", "server.js"],
        cwd=workspace_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(40):
            try:
                status, _, payload = request_json(base_url, "GET", "/health")
                if status == 200 and payload.get("ok") is True:
                    break
            except Exception:
                pass
            time.sleep(0.25)
        else:
            output = process.stdout.read() if process.stdout else ""
            raise AssertionError(f"server failed to start:\n{output}")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture
def server():
    with running_server() as base_url:
        yield base_url


def build_alternate_fixture() -> tuple[Path, Path]:
    temp_root = Path(tempfile.mkdtemp(prefix="backend-template-alt-"))
    data_dir = temp_root / "data"
    state_dir = temp_root / "state"
    shutil.copytree(DATA_ROOT, data_dir)
    shutil.copytree(STATE_ROOT, state_dir)

    orders = read_json(data_dir / "orders_snapshot.json")
    customers = read_json(data_dir / "customers_snapshot.json")
    customers.append(
        {
            "id": "cust_099",
            "name": "Nina Campos",
            "email": "nina.campos@example.com",
            "default_address": {"country_code": "US", "city": "Austin"},
        }
    )
    inserted = {
        "id": "ord_1099",
        "number": "1099",
        "created_at": "2026-04-18T10:00:00Z",
        "financial_status": "paid",
        "fulfillment_status": "fulfilled",
        "currency": "USD",
        "subtotal_price": 72.0,
        "total_price": 78.0,
        "refundable_amount": 78.0,
        "cancelled_at": None,
        "customer_id": "cust_099",
        "line_items": [
            {
                "id": "li_1099_1",
                "sku": "BOTTLE-TRAVEL-RED",
                "title": "Travel Bottle",
                "quantity": 2,
                "unit_price": 36.0,
            }
        ],
    }
    shuffled = [orders[3], orders[0], inserted, orders[7], orders[2], orders[5], orders[1], orders[6], orders[4]]
    (data_dir / "orders_snapshot.json").write_text(json.dumps(shuffled, indent=2) + "\n", encoding="utf-8")
    (data_dir / "customers_snapshot.json").write_text(json.dumps(customers, indent=2) + "\n", encoding="utf-8")
    return data_dir, state_dir
