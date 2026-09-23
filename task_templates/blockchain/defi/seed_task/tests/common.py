from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_DIR", "/root/workspace"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_DIR", "/root/output"))
REPORT_PATH = WORKSPACE_ROOT / "out" / "launch_report.json"
SPEC_ROOT = WORKSPACE_ROOT / "spec"

SPEC_HASH_PATH = Path(os.environ.get("TASK_SPEC_HASH_PATH", "/opt/defi-spec.sha256"))

TESTS_ROOT = Path(__file__).resolve().parent
QUERY_STATE_SCRIPT = TESTS_ROOT / "query_state.js"


def sha256_listing(path: Path) -> str:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    for item in files:
        rel = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(hashlib.sha256(item.read_bytes()).digest())
        digest.update(b"\n")
    return digest.hexdigest()


def sha256sum_style_listing(path: Path) -> str:
    return subprocess.check_output(
        f"find {path} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )


def run_replay(workspace_root: Path = WORKSPACE_ROOT, timeout_sec: int = 900) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TASK_WORKSPACE_ROOT"] = str(workspace_root)
    env["TASK_WORKSPACE_DIR"] = str(workspace_root)
    env["TASK_OUTPUT_DIR"] = str(workspace_root / "out")
    return subprocess.run(
        ["bash", str(workspace_root / "run_launch.sh")],
        cwd=workspace_root,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
        env=env,
    )


def run_replay_in_temp(workspace_root: Path = WORKSPACE_ROOT) -> tuple[subprocess.CompletedProcess[str], Path]:
    temp_root = Path(tempfile.mkdtemp(prefix="defi-replay-"))
    workspace_copy = temp_root / "workspace"
    shutil.copytree(workspace_root, workspace_copy)
    node_modules = workspace_copy / "node_modules"
    if node_modules.exists():
        shutil.rmtree(node_modules)
    subprocess.run(
        ["npm", "install"],
        cwd=workspace_copy,
        text=True,
        capture_output=True,
        timeout=900,
        check=True,
    )
    result = run_replay(workspace_copy)
    return result, workspace_copy


def run_replay_in_temp_with_spec_overrides(
    overrides: dict[str, str], workspace_root: Path = WORKSPACE_ROOT
) -> tuple[subprocess.CompletedProcess[str], Path]:
    temp_root = Path(tempfile.mkdtemp(prefix="defi-replay-"))
    workspace_copy = temp_root / "workspace"
    shutil.copytree(workspace_root, workspace_copy)
    for rel_path, content in overrides.items():
        target = workspace_copy / "spec" / rel_path
        target.write_text(content, encoding="utf-8")
    node_modules = workspace_copy / "node_modules"
    if node_modules.exists():
        shutil.rmtree(node_modules)
    subprocess.run(
        ["npm", "install"],
        cwd=workspace_copy,
        text=True,
        capture_output=True,
        timeout=900,
        check=True,
    )
    result = run_replay(workspace_copy)
    return result, workspace_copy


def run_hardhat_script(script_path: Path, workspace_root: Path = WORKSPACE_ROOT, timeout_sec: int = 900) -> str:
    env = os.environ.copy()
    env["TASK_WORKSPACE_ROOT"] = str(workspace_root)
    env["TASK_WORKSPACE_DIR"] = str(workspace_root)
    env["TASK_OUTPUT_DIR"] = str(workspace_root / "out")
    node_path = str(workspace_root / "node_modules")
    env["NODE_PATH"] = node_path + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
    return subprocess.check_output(
        ["npx", "hardhat", "run", str(script_path), "--network", "hardhat", "--no-compile"],
        cwd=workspace_root,
        text=True,
        timeout=timeout_sec,
        env=env,
    )


def load_report(path: Path = REPORT_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_query_state(report_path: Path) -> dict:
    out = subprocess.check_output(
        ["node", str(QUERY_STATE_SCRIPT), str(report_path)],
        text=True,
    )
    return json.loads(out)


def as_int(value) -> int:
    return int(value)


def get_actor_summaries(report: dict) -> dict:
    return report.get("actor_summaries", {})


def get_lp_balance_actors(report: dict) -> list[str]:
    balances = report.get("pair", {}).get("lp_balances")
    if isinstance(balances, dict):
        return sorted(balances.keys())
    actors = []
    for name, summary in get_actor_summaries(report).items():
        if "lp_balance" in summary or "staked_lp" in summary or "staked_lp_balance" in summary:
            actors.append(name)
    return sorted(actors)


def get_staker_actors(report: dict) -> list[str]:
    balances = report.get("reward_program", {}).get("staker_balances")
    if isinstance(balances, dict):
        return sorted(balances.keys())
    actors = []
    for name, summary in get_actor_summaries(report).items():
        if "staked_lp" in summary or "staked_lp_balance" in summary:
            actors.append(name)
    return sorted(actors)


def get_current_vote_actors(report: dict) -> list[str]:
    actors = set()
    current_votes = report.get("governance_token", {}).get("current_votes")
    if isinstance(current_votes, dict):
        actors.update(current_votes.keys())
    for name, summary in get_actor_summaries(report).items():
        if "votes" in summary or "delegated_voting_power" in summary or "voting_power" in summary:
            actors.add(name)
    if report.get("scenario_results"):
        latest_actor_state = report["scenario_results"][-1].get("actors", {})
        for name, summary in latest_actor_state.items():
            if "votes" in summary or "delegated_voting_power" in summary or "voting_power" in summary:
                actors.add(name)
    return sorted(actors)


def get_proposal_status(report: dict) -> dict | None:
    governance_token = report.get("governance_token", {})
    for key in ("proposal_status", "active_proposal", "proposal", "latest_proposal"):
        value = governance_token.get(key)
        if isinstance(value, dict):
            return value

    for item in reversed(report.get("scenario_results", [])):
        governance = item.get("governance")
        if not isinstance(governance, dict):
            continue
        for key in ("proposal_status", "active_proposal", "proposal", "latest_proposal"):
            value = governance.get(key)
            if isinstance(value, dict):
                return value
    return None


def proposal_value(proposal: dict, *names: str):
    for name in names:
        if name in proposal:
            return proposal[name]
    raise KeyError(f"Missing proposal fields: {names}")
