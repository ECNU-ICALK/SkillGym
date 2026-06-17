from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "environment" / "workspace"
OUTPUT_ROOT = WORKSPACE / "output"
DATA_ROOT = WORKSPACE / "data" / "upstream"
SCRIPTS_ROOT = WORKSPACE / "scripts"
AGENT_LOG = Path(os.environ.get("AGENT_LOG", "/logs/agent/codex.txt"))

EXPECTED_BASE_DIGEST = "116c118e7435741769eeed05dbf54e3ae77b11dd975ec88613a00011f27c480c"


def script_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["WORKSPACE_DIR"] = str(WORKSPACE)
    if extra:
        env.update(extra)
    return env


def run_script(script_name: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPTS_ROOT / script_name)],
        cwd=WORKSPACE,
        env=script_env(env),
        text=True,
        capture_output=True,
        check=True,
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def wait_for_health(url: str, attempts: int = 90) -> None:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise AssertionError(f"Timed out waiting for {url}")


def start_server(port: int = 3300, scenario_id: str = "docs-segment-cache") -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [str(SCRIPTS_ROOT / "start_dev.sh")],
        cwd=WORKSPACE,
        env=script_env({"PORT": str(port), "SCENARIO_ID": scenario_id}),
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_health(f"http://localhost:{port}/health")
    return process


def stop_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def reset_output_dir() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def build_alternate_snapshot() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="segment-cache-routes."))
    routes = load_json(DATA_ROOT / "docs_route_snapshot.json")
    routes.insert(
        4,
        {
            "route": "/docs/app/api-reference/config/next-config-js/cacheLife",
            "title": "cacheLife",
            "section": "config",
            "docType": "api-reference",
            "pathSegments": [
                "docs",
                "app",
                "api-reference",
                "config",
                "next-config-js",
                "cacheLife",
            ],
            "sourceUrl": "https://nextjs.org/docs/app/api-reference/config/next-config-js/cacheLife",
            "wordCount": 360,
        },
    )
    target = temp_dir / "docs_route_snapshot_alt.json"
    target.write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")
    return target


def find_skill_file() -> Path | None:
    candidates = [
        ROOT / "environment" / "skills" / "flags" / "SKILL.md",
        Path("/logs/agent/skills/flags/SKILL.md"),
        Path("/root/environment/skills/flags/SKILL.md"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
