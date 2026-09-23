from __future__ import annotations

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


TASK_ROOT = Path("/app") if Path("/app/workspace").exists() else Path(__file__).resolve().parents[1] / "environment"
WORKSPACE_ROOT = TASK_ROOT / "workspace"
DATA_ROOT = WORKSPACE_ROOT / "data"
STATE_ROOT = WORKSPACE_ROOT / "state"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def request_text(
    base_url: str,
    method: str,
    path: str,
    *,
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], str]:
    request_headers = {}
    if api_key is not None:
        request_headers["X-Partner-Key"] = api_key
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(
        urllib.parse.urljoin(base_url, path),
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode("utf-8")


def runtime_export_files(state_dir: Path = STATE_ROOT) -> list[Path]:
    root = state_dir.parent / "output" / "exports"
    return sorted(root.glob("*.csv"))


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
    env["OUTPUT_DIR"] = str(state_dir.parent / "output" / "exports")
    if not env.get("EXPORT_SIGNING_SECRET"):
        env["EXPORT_SIGNING_SECRET"] = "task-export-signing-secret"
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


def build_alternate_fixture() -> tuple[Path, Path]:
    temp_root = Path(tempfile.mkdtemp(prefix="security-template-alt-"))
    data_dir = temp_root / "data"
    state_dir = temp_root / "state"
    output_dir = temp_root / "output" / "exports"
    shutil.copytree(DATA_ROOT, data_dir)
    shutil.copytree(STATE_ROOT, state_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    advisories = []
    for line in (data_dir / "nvd_cves.ndjson").read_text(encoding="utf-8").splitlines():
        if line.strip():
            advisories.append(json.loads(line))
    advisories.append(
        {
            "cve_id": "CVE-2099-0001",
            "published": "2026-04-01T00:00:00Z",
            "modified": "2026-04-02T00:00:00Z",
            "vendor": "progress",
            "product": "moveit_gateway",
            "severity": "high",
            "cvss_v3_base_score": 8.8,
            "epss": 0.01111,
            "kev": False,
            "description": "Synthetic advisory used to verify data-driven behavior.",
            "references": ["https://example.invalid/advisory/CVE-2099-0001"]
        }
    )
    (data_dir / "nvd_cves.ndjson").write_text("\n".join(json.dumps(row) for row in advisories) + "\n", encoding="utf-8")

    kev_catalog = read_json(data_dir / "kev_catalog.json")
    kev_catalog["vulnerabilities"].append(
        {
            "cveID": "CVE-2099-0001",
            "vendorProject": "Progress",
            "product": "MOVEit Gateway",
            "vulnerabilityName": "Synthetic Guardrail Entry",
            "dateAdded": "2026-04-03",
            "dueDate": "2026-04-24",
            "requiredAction": "Apply vendor-provided fixes or mitigations.",
            "knownRansomwareCampaignUse": "Unknown"
        }
    )
    (data_dir / "kev_catalog.json").write_text(json.dumps(kev_catalog, indent=2) + "\n", encoding="utf-8")

    with (data_dir / "epss_scores.csv").open("a", encoding="utf-8") as handle:
        handle.write("CVE-2099-0001,0.95123,0.99501\n")
    return data_dir, state_dir
