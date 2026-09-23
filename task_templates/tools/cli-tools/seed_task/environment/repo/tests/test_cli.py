from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATA = ROOT / "tests" / "fixtures" / "ourairports"
FIXTURE_CONTRACT = ROOT / "tests" / "fixtures" / "contracts" / "release_contract.json"
BUILD_ROOT = ROOT / "build"


def ensure_release_prereqs(include_package_lock: bool = False) -> None:
    pydeps = BUILD_ROOT / "pydeps"
    pydeps.mkdir(parents=True, exist_ok=True)
    (pydeps / ".ready").write_text("", encoding="utf-8")
    if include_package_lock:
        BUILD_ROOT.mkdir(parents=True, exist_ok=True)
        (BUILD_ROOT / "package.lock").write_text("", encoding="utf-8")


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "airdesk", "--data-dir", str(FIXTURE_DATA), *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def test_version() -> None:
    proc = run_cli("version", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == {"package_name": "airdesk", "version": "0.4.0"}


def test_stats() -> None:
    proc = run_cli("stats", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == {
        "airports": 3,
        "countries": 2,
        "frequencies": 3,
        "regions": 3,
        "runways": 3,
    }


def test_airport_found() -> None:
    proc = run_cli("airport", "KJFK", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["icao"] == "KJFK"
    assert payload["frequency_count"] == 2
    assert payload["longest_runway_ft"] == "14572"


def test_country_limit() -> None:
    proc = run_cli("country", "US", "--limit", "1", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["country_code"] == "US"
    assert payload["returned"] == 1
    assert payload["airports"][0]["ident"] == "KJFK"


def test_release_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ensure_release_prereqs(include_package_lock=True)
        proc = run_cli(
            "release",
            "--contract",
            str(FIXTURE_CONTRACT),
            "--output-dir",
            tmpdir,
            "--build-target",
            "make package",
            "--require-package-lock",
            "--format",
            "json",
        )
        assert proc.returncode == 0, proc.stderr
        manifest = json.loads(proc.stdout)
        out_dir = Path(tmpdir)
        assert manifest["artifact_name"] == "airdesk_0.4.0_linux_amd64.tar.gz"
        assert manifest["build_target"] == "make package"
        for filename in (
            "release_manifest.json",
            "smoke_expected.json",
            "sha256sums.txt",
            "command_catalog.md",
            "airdesk_0.4.0_linux_amd64.tar.gz",
        ):
            assert (out_dir / filename).exists(), filename

        with tarfile.open(out_dir / "airdesk_0.4.0_linux_amd64.tar.gz", "r:gz") as archive:
            names = sorted(archive.getnames())
        assert "airdesk_0.4.0_linux_amd64/bin/airdesk" in names
