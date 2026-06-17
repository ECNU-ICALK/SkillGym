from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE_ROOT = Path("/workspace")
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT))
if not (WORKSPACE_ROOT / "pkgmeta-kit").exists():
    WORKSPACE_ROOT = TASK_ROOT / "environment" / "workspace"

REPO_ROOT = WORKSPACE_ROOT / "pkgmeta-kit"
OUT_ROOT = WORKSPACE_ROOT / "out"
DIST_DIR = REPO_ROOT / "dist"
CONTRACT_PATH = REPO_ROOT / "contracts" / "cli_contract.json"
AUTOMATION_CONTRACT_PATH = REPO_ROOT / "contracts" / "automation_contract.json"
LICENSES_PATH = REPO_ROOT / "data" / "licenses.json"
CLASSIFIERS_PATH = REPO_ROOT / "data" / "trove_classifiers.py"
MANIFEST_PATH = OUT_ROOT / "release_manifest.json"


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_automation_contract() -> dict[str, Any]:
    return json.loads(AUTOMATION_CONTRACT_PATH.read_text(encoding="utf-8"))


def load_licenses() -> list[dict[str, Any]]:
    payload = json.loads(LICENSES_PATH.read_text(encoding="utf-8"))
    return list(payload["licenses"])


def load_classifiers() -> list[str]:
    namespace = runpy.run_path(str(CLASSIFIERS_PATH))
    return sorted(namespace["classifiers"])


def expected_snapshot(limit: int) -> dict[str, Any]:
    licenses = load_licenses()
    classifiers = load_classifiers()
    counts = Counter(value.split(" :: ", 1)[0] for value in classifiers)
    top = [
        {"root": root, "count": count}
        for root, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]
    return {
        "license_count": len(licenses),
        "osi_approved_count": sum(1 for row in licenses if row.get("isOsiApproved")),
        "deprecated_license_count": sum(1 for row in licenses if row.get("isDeprecatedLicenseId")),
        "classifier_count": len(classifiers),
        "top_classifier_roots": top,
    }


def expected_license_lookup(license_id: str) -> dict[str, Any]:
    item = next(row for row in load_licenses() if row["licenseId"] == license_id)
    return {
        "id": item["licenseId"],
        "name": item["name"],
        "osi_approved": bool(item.get("isOsiApproved")),
        "deprecated": bool(item.get("isDeprecatedLicenseId")),
        "reference_count": len(item.get("seeAlso", [])),
    }


def expected_classifier_prefix(prefix: str, limit: int | None) -> dict[str, Any]:
    matches = [value for value in load_classifiers() if value.startswith(prefix)]
    if limit is not None:
        matches = matches[:limit]
    return {
        "prefix": prefix,
        "matches": matches,
        "match_count": len(matches),
    }


def read_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def list_artifacts() -> tuple[Path, Path]:
    wheels = sorted(DIST_DIR.glob("*.whl"))
    sdists = sorted(DIST_DIR.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected 1 wheel, found {wheels}"
    assert len(sdists) == 1, f"expected 1 sdist, found {sdists}"
    return wheels[0], sdists[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wheel_entries(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return sorted(archive.namelist())


def sdist_entries(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        return sorted(member.name for member in archive.getmembers() if member.isfile())


def wheel_metadata_text(path: Path, suffix: str) -> str:
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith(suffix):
                return archive.read(name).decode("utf-8")
    raise AssertionError(f"missing {suffix} in {path}")


def create_isolated_python(venv_dir: Path) -> Path:
    created = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if created.returncode != 0:
        subprocess.run([sys.executable, "-m", "virtualenv", str(venv_dir)], check=True)
    return venv_dir / "bin" / "python"


def run_installed(argv: list[str]) -> tuple[int, str, str]:
    wheel, _ = list_artifacts()
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-venv-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", str(wheel)], check=True, env=env)
        command = [str(python_bin), *argv]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def run_console_script(argv: list[str]) -> tuple[int, str, str]:
    wheel, _ = list_artifacts()
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-cli-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        cli_bin = venv_dir / "bin" / "pkgmeta-kit"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", str(wheel)], check=True, env=env)
        completed = subprocess.run(
            [str(cli_bin), *argv],
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def run_installed_from_sdist(argv: list[str]) -> tuple[int, str, str]:
    _, sdist = list_artifacts()
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-sdist-venv-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", str(sdist)], check=True, env=env)
        command = [str(python_bin), *argv]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def run_console_script_from_sdist(argv: list[str]) -> tuple[int, str, str]:
    _, sdist = list_artifacts()
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-sdist-cli-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        cli_bin = venv_dir / "bin" / "pkgmeta-kit"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", str(sdist)], check=True, env=env)
        completed = subprocess.run(
            [str(cli_bin), *argv],
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def run_installed_entry_point(group: str, name: str, from_sdist: bool = False) -> tuple[int, str, str]:
    wheel, sdist = list_artifacts()
    artifact = sdist if from_sdist else wheel
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-entrypoint-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", str(artifact)], check=True, env=env)
        code = (
            "import importlib.metadata as metadata, json\n"
            f"group = {group!r}\n"
            f"name = {name!r}\n"
            "matches = [entry_point for entry_point in metadata.entry_points(group=group) if entry_point.name == name]\n"
            "if len(matches) != 1:\n"
            "    raise SystemExit(f'expected exactly one entry point for {group}:{name}, found {len(matches)}')\n"
            "payload = matches[0].load()()\n"
            "print(json.dumps(payload, indent=2, sort_keys=True))\n"
        )
        completed = subprocess.run(
            [str(python_bin), "-c", code],
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def run_installed_root_api(from_sdist: bool = False) -> tuple[int, str, str]:
    wheel, sdist = list_artifacts()
    artifact = sdist if from_sdist else wheel
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-root-api-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", str(artifact)], check=True, env=env)
        code = (
            "import json\n"
            "from pkgmeta_kit import catalog_summary, snapshot\n"
            "payload = {'snapshot': snapshot(), 'catalog_summary': catalog_summary()}\n"
            "print(json.dumps(payload, indent=2, sort_keys=True))\n"
        )
        completed = subprocess.run(
            [str(python_bin), "-c", code],
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def run_installed_mypy_probe(from_sdist: bool = False) -> tuple[int, str, str]:
    wheel, sdist = list_artifacts()
    artifact = sdist if from_sdist else wheel
    with tempfile.TemporaryDirectory(prefix="pkgmeta-kit-mypy-") as tempdir:
        temp = Path(tempdir)
        venv_dir = temp / "venv"
        python_bin = create_isolated_python(venv_dir)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python_bin), "-m", "pip", "install", "--quiet", "mypy", str(artifact)], check=True, env=env)
        consumer = temp / "typed_consumer.py"
        consumer.write_text(
            "from pkgmeta_kit import catalog_summary, snapshot\n"
            "\n"
            "catalog_payload = catalog_summary()\n"
            "snapshot_payload = snapshot()\n"
            "\n"
            "assert catalog_payload['license_count'] >= 0\n"
            "assert snapshot_payload['classifier_count'] >= 0\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            [str(python_bin), "-m", "mypy", "--strict", str(consumer)],
            check=False,
            capture_output=True,
            text=True,
            cwd=temp,
            env=env,
        )
        return completed.returncode, completed.stdout, completed.stderr


def parse_json_output(stdout: str, stderr: str) -> dict[str, Any]:
    assert not stderr.strip(), stderr
    return json.loads(stdout)


def original_input_hashes() -> dict[str, str]:
    return {
        "licenses.json": sha256_file(LICENSES_PATH),
        "trove_classifiers.py": sha256_file(CLASSIFIERS_PATH),
    }


def dynamic_license_id() -> str:
    for candidate in load_licenses():
        identifier = candidate["licenseId"]
        if identifier not in {"MIT"} and identifier.startswith("Apache-"):
            return identifier
    raise AssertionError("unable to derive dynamic Apache license id")


def dynamic_classifier_prefix() -> tuple[str, int]:
    candidates = ["Programming Language :: Python :: 3", "Topic ::", "Framework ::"]
    classifiers = load_classifiers()
    for prefix in candidates:
        count = sum(1 for item in classifiers if item.startswith(prefix))
        if count >= 3:
            return prefix, 3
    raise AssertionError("unable to derive dynamic classifier prefix")
