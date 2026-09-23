from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from conftest import (
    DATA_ROOT,
    TASK_ROOT,
    build_alternate_fixture,
    request_json,
    running_server,
    runtime_refund_count,
)


FULL_KEY = "pk_live_gold_partner"
AGENT_LOG = Path("/logs/agent/codex.txt")


def _full_data_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.iterdir()):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_static_input_data_unchanged() -> None:
    assert _full_data_hash(DATA_ROOT) == "fdf02e66377c322ad1a9166cb0d3073b49212ba911da7282c728143a56690e75"


def test_behavior_generalizes_on_alternate_fixture() -> None:
    alt_data_dir, alt_state_dir = build_alternate_fixture()
    try:
        with running_server(data_dir=alt_data_dir, state_dir=alt_state_dir) as base_url:
            status1, _, payload1 = request_json(
                base_url,
                "GET",
                "/api/v1/orders?page=1&page_size=2&status=paid&sort=-created_at",
                api_key=FULL_KEY,
            )
            status1b, _, payload1b = request_json(
                base_url,
                "GET",
                "/api/v1/orders?page=1&page_size=2&status=paid&sort=-created_at",
                api_key=FULL_KEY,
            )
            assert status1 == 200, payload1
            assert status1b == 200, payload1b
            assert [row["id"] for row in payload1["data"]] == ["ord_1099", "ord_1008"]
            assert [row["id"] for row in payload1b["data"]] == ["ord_1099", "ord_1008"]

            before = runtime_refund_count(state_dir=alt_state_dir)
            first_status, _, first_body = request_json(
                base_url,
                "POST",
                "/api/v1/refunds",
                api_key=FULL_KEY,
                headers={"Idempotency-Key": "alt-idem-1099"},
                payload={"order_id": "ord_1099", "amount": 15.0, "reason": "customer_request"},
            )
            replay_status, _, replay_body = request_json(
                base_url,
                "POST",
                "/api/v1/refunds",
                api_key=FULL_KEY,
                headers={"Idempotency-Key": "alt-idem-1099"},
                payload={"order_id": "ord_1099", "amount": 15.0, "reason": "customer_request"},
            )
            assert first_status == 201, first_body
            assert replay_status in {200, 201}, replay_body
            assert replay_body["data"]["id"] == first_body["data"]["id"]
            assert runtime_refund_count(state_dir=alt_state_dir) == before + 1
    finally:
        shutil.rmtree(alt_data_dir.parent)


def test_bound_skill_workflow_can_be_consulted_if_present() -> None:
    skill_md = Path("/logs/agent/skills/api-design/SKILL.md")
    if not skill_md.exists() or not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert "/logs/agent/skills/api-design/SKILL.md" in text or "/root/.codex/skills/api-design/SKILL.md" in text


def test_task_kept_expected_structure() -> None:
    assert Path("/app/workspace/server.js").exists() or (TASK_ROOT / "workspace" / "server.js").exists()
    assert Path("/app/workspace/service/app.js").exists() or (TASK_ROOT / "workspace" / "service" / "app.js").exists()
    assert Path("/tests/test.sh").exists() or (TASK_ROOT.parent / "tests" / "test.sh").exists()
