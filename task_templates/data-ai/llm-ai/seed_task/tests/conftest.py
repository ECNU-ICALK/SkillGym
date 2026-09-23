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


LOCAL_TASK_ROOT = Path("/home/lenovo/skill/Harbor/skill_moban/development/llm-ai/template_new/environment")
if Path("/app/workspace/server.js").exists() and Path("/services/provider-sim/src/server.js").exists():
    TASK_ROOT = Path("/app")
    PROVIDER_ROOT = Path("/services/provider-sim")
else:
    TASK_ROOT = LOCAL_TASK_ROOT
    PROVIDER_ROOT = LOCAL_TASK_ROOT / "provider-sim"
WORKSPACE_ROOT = TASK_ROOT / "workspace"
DATA_ROOT = WORKSPACE_ROOT / "data"
STATE_ROOT = WORKSPACE_ROOT / "state"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def static_data_hash(root: Path = DATA_ROOT) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def reset_runtime_state(workspace_root: Path = WORKSPACE_ROOT, *, data_dir: Path | None = None, state_dir: Path | None = None) -> None:
    env = os.environ.copy()
    if data_dir is not None:
        env["DATA_DIR"] = str(data_dir)
    if state_dir is not None:
        env["STATE_DIR"] = str(state_dir)
    subprocess.run(["node", "scripts/reset_runtime_state.js"], cwd=workspace_root, env=env, check=True, capture_output=True, text=True)


def request_json(base_url: str, method: str, path: str, *, payload: dict | None = None) -> tuple[int, dict[str, str], dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(urllib.parse.urljoin(base_url, path), data=body, headers={"Content-Type": "application/json"} if body is not None else {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, dict(resp.headers), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), json.loads(exc.read().decode("utf-8"))


def provider_request_count(state_dir: Path = STATE_ROOT) -> int:
    return len(read_json(state_dir / "runtime_state.json")["provider_requests"])


def service_request_count(state_dir: Path = STATE_ROOT) -> int:
    return len(read_json(state_dir / "runtime_state.json")["service_requests"])


@contextmanager
def running_stack(*, workspace_root: Path = WORKSPACE_ROOT, provider_root: Path = PROVIDER_ROOT, data_dir: Path = DATA_ROOT, state_dir: Path = STATE_ROOT) -> str:
    reset_runtime_state(workspace_root=workspace_root, data_dir=data_dir, state_dir=state_dir)
    provider_port = _free_port()
    service_port = _free_port()

    provider_env = os.environ.copy()
    provider_env["PORT"] = str(provider_port)
    provider_env["DATA_DIR"] = str(data_dir)
    provider_env["STATE_DIR"] = str(state_dir)
    provider_proc = subprocess.Popen(["node", "src/server.js"], cwd=provider_root, env=provider_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    service_env = os.environ.copy()
    service_env["PORT"] = str(service_port)
    service_env["DATA_DIR"] = str(data_dir)
    service_env["STATE_DIR"] = str(state_dir)
    service_env["PROVIDER_BASE_URL"] = f"http://127.0.0.1:{provider_port}"
    service_proc = subprocess.Popen(["node", "server.js"], cwd=workspace_root, env=service_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    provider_url = f"http://127.0.0.1:{provider_port}"
    service_url = f"http://127.0.0.1:{service_port}"
    try:
        for _ in range(50):
            ready = 0
            try:
                status, _, payload = request_json(provider_url, "GET", "/health")
                if status == 200 and payload.get("ok") is True:
                    ready += 1
            except Exception:
                pass
            try:
                status, _, payload = request_json(service_url, "GET", "/health")
                if status == 200 and payload.get("ok") is True:
                    ready += 1
            except Exception:
                pass
            if ready == 2:
                break
            time.sleep(0.25)
        else:
            provider_output = provider_proc.stdout.read() if provider_proc.stdout else ""
            service_output = service_proc.stdout.read() if service_proc.stdout else ""
            raise AssertionError(f"stack failed to start\nprovider:\n{provider_output}\nservice:\n{service_output}")
        yield service_url
    finally:
        for proc in [service_proc, provider_proc]:
            proc.terminate()
        for proc in [service_proc, provider_proc]:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def build_alternate_fixture() -> tuple[Path, Path]:
    temp_root = Path(tempfile.mkdtemp(prefix="llm-ai-template-alt-"))
    data_dir = temp_root / "data"
    state_dir = temp_root / "state"
    shutil.copytree(DATA_ROOT, data_dir)
    shutil.copytree(STATE_ROOT, state_dir)

    bank_path = data_dir / "tickets" / "banking77_curated.jsonl"
    bank_rows = read_jsonl(bank_path)
    bank_rows.append({"id": "bank_099", "dataset": "banking77", "text": "A card payment I made online shows as reversed and I need an explanation.", "channel": "chat", "language": "en", "priority": "normal", "customer_tier": "standard", "expected_intent": "cash_withdrawal_reverted", "live_failure_mode": None})
    bank_rows.append({"id": "bank_109", "dataset": "banking77", "text": "The beneficiary setup keeps failing after I updated the details and I need the maintenance steps again.", "channel": "email", "language": "en", "priority": "normal", "customer_tier": "standard", "expected_intent": "beneficiary_not_defined", "live_failure_mode": "invalid_json"})
    bank_rows.append({"id": "bank_110", "dataset": "banking77", "text": "Please confirm the beneficiary update checklist because the app flow still looks incomplete.", "channel": "chat", "language": "en", "priority": "normal", "customer_tier": "premium", "expected_intent": "beneficiary_not_defined", "live_failure_mode": "invalid_payload"})
    bank_rows.append({"id": "bank_111", "dataset": "banking77", "text": "The beneficiary setup is still blocked, but I only need the confirmed maintenance checklist we already use.", "channel": "chat", "language": "en", "priority": "normal", "customer_tier": "standard", "expected_intent": "beneficiary_not_defined", "live_failure_mode": "retryable"})
    bank_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in bank_rows), encoding="utf-8")

    triage_cases_path = data_dir / "sandbox_cases" / "triage_cases.json"
    triage_cases = read_json(triage_cases_path)
    triage_cases["bank_099"] = {"ticket_id": "bank_099", "status": "success", "queue": "card-ops", "intent": "cash_withdrawal_reverted", "recommended_action": "explain_reverted_card_payment", "evidence": [{"source_id": "kb:card-reverted-payment", "snippet": "Reverted card payments are usually released automatically if the merchant did not capture the authorization."}], "escalation_reason": None}
    triage_cases["bank_109"] = {"ticket_id": "bank_109", "status": "success", "queue": "profile-maintenance", "intent": "beneficiary_not_defined", "recommended_action": "guide_joint_beneficiary_update_steps", "evidence": [], "escalation_reason": None}
    triage_cases["bank_110"] = {"ticket_id": "bank_110", "status": "success", "queue": "profile-maintenance", "intent": "beneficiary_not_defined", "recommended_action": "guide_joint_beneficiary_update_steps", "evidence": [], "escalation_reason": None}
    triage_cases["bank_111"] = {"ticket_id": "bank_111", "status": "success", "queue": "profile-maintenance", "intent": "beneficiary_not_defined", "recommended_action": "guide_joint_beneficiary_update_steps", "evidence": [], "escalation_reason": None}
    triage_cases_path.write_text(json.dumps(triage_cases, indent=2) + "\n", encoding="utf-8")

    review_cases_path = data_dir / "sandbox_cases" / "review_cases.json"
    review_cases = read_json(review_cases_path)
    review_cases["bank_099"] = {"ticket_id": "bank_099", "disposition": "send_knowledge_reply", "review_note": "Explain that reversed card authorizations usually drop off automatically if the merchant did not capture them.", "evidence": [{"source_id": "kb:card-reverted-payment", "snippet": "Reverted card payments are usually released automatically if the merchant did not capture the authorization."}], "escalation_reason": None}
    review_cases["bank_109"] = {"ticket_id": "bank_109", "disposition": "send_knowledge_reply", "review_note": "Share the joint beneficiary maintenance checklist and confirm the supported fallback verification path.", "evidence": [], "escalation_reason": None}
    review_cases["bank_110"] = {"ticket_id": "bank_110", "disposition": "send_knowledge_reply", "review_note": "Share the joint beneficiary maintenance checklist and confirm the supported fallback verification path.", "evidence": [], "escalation_reason": None}
    review_cases["bank_111"] = {"ticket_id": "bank_111", "disposition": "send_knowledge_reply", "review_note": "Share the joint beneficiary maintenance checklist and confirm the supported fallback verification path.", "evidence": [], "escalation_reason": None}
    review_cases_path.write_text(json.dumps(review_cases, indent=2) + "\n", encoding="utf-8")

    return data_dir, state_dir
