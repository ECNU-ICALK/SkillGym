from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WORKSPACE_ROOT = Path(os.environ.get("AIRPORT_WORKSPACE_ROOT", "/app/workspace"))
TESTS_ROOT = WORKSPACE_ROOT / "tests"
DATA_ROOT = WORKSPACE_ROOT / "data"
VERIFIER_LOG_ROOT = Path(os.environ.get("VERIFIER_LOG_ROOT", "/logs/verifier"))
ACCESS_LOG_PATH = Path(os.environ.get("AIRPORT_OPS_ACCESS_LOG", "/tmp/airport-ops-access.log"))
APP_HASH_PATH = Path(os.environ.get("AIRPORT_APP_HASH_PATH", "/opt/airport-app.sha256"))
DATA_HASH_PATH = Path(os.environ.get("AIRPORT_DATA_HASH_PATH", "/opt/airport-data.sha256"))


@dataclass(frozen=True)
class SuiteResult:
    exit_code: int
    stdout: str
    stderr: str


_SUITE_RESULTS: dict[str, SuiteResult] = {}


def access_log_path_for(mutation_mode: str | None = None) -> Path:
    if not mutation_mode:
        return ACCESS_LOG_PATH
    slug = mutation_mode.replace("/", "-").replace(" ", "-")
    return ACCESS_LOG_PATH.with_name(f"{ACCESS_LOG_PATH.stem}-{slug}{ACCESS_LOG_PATH.suffix}")


def workspace_test_text() -> str:
    text_parts = []
    for path in sorted(TESTS_ROOT.rglob("*.js")):
        text_parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(text_parts)


def run_user_suite(mutation_mode: str | None = None) -> SuiteResult:
    key = mutation_mode or "base"
    if key in _SUITE_RESULTS:
        return _SUITE_RESULTS[key]

    access_log_path = access_log_path_for(mutation_mode)
    access_log_path.unlink(missing_ok=True)
    VERIFIER_LOG_ROOT.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        ["npm", "test", "--", "--reporter=line"],
        cwd=WORKSPACE_ROOT,
        env={
            **os.environ,
            "CI": "1",
            "AIRPORT_OPS_ACCESS_LOG": str(access_log_path),
            **({"AIRPORT_OPS_MUTATION_MODE": mutation_mode} if mutation_mode else {}),
        },
        capture_output=True,
        text=True,
        timeout=420,
    )

    suffix = "" if not mutation_mode else f".{mutation_mode}"
    (VERIFIER_LOG_ROOT / f"npm-test{suffix}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (VERIFIER_LOG_ROOT / f"npm-test{suffix}.stderr.txt").write_text(completed.stderr, encoding="utf-8")

    _SUITE_RESULTS[key] = SuiteResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    return _SUITE_RESULTS[key]


def load_access_log(path: Path | None = None) -> list[dict]:
    access_log_path = path or ACCESS_LOG_PATH
    if not access_log_path.exists():
        return []

    rows = []
    for line in access_log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def search_log_entries(kind: str, path: Path | None = None) -> list[dict]:
    return [row for row in load_access_log(path) if row.get("kind") == kind]


def manifest_for_paths(paths: Iterable[Path]) -> dict[str, str]:
    manifest = {}
    for path in sorted(paths):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest[str(path)] = digest
    return manifest


def read_manifest(path: Path) -> dict[str, str]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {}

    manifest: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, file_path = line.split("  ", 1)
        manifest[file_path] = digest
    return manifest


def current_workspace_manifest() -> dict[str, str]:
    targets = [
        WORKSPACE_ROOT / "server.js",
        WORKSPACE_ROOT / "public",
        WORKSPACE_ROOT / "package.json",
        WORKSPACE_ROOT / "package-lock.json",
        WORKSPACE_ROOT / "playwright.config.js",
    ]
    paths = []
    for target in targets:
        if target.is_dir():
            paths.extend(path for path in target.rglob("*") if path.is_file())
        elif target.is_file():
            paths.append(target)
    return manifest_for_paths(paths)


def current_data_manifest() -> dict[str, str]:
    return manifest_for_paths(path for path in DATA_ROOT.rglob("*") if path.is_file())


def baseline_workspace_manifest() -> dict[str, str]:
    return read_manifest(APP_HASH_PATH)


def baseline_data_manifest() -> dict[str, str]:
    return read_manifest(DATA_HASH_PATH)
