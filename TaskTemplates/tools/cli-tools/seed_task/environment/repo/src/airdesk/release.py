from __future__ import annotations

import hashlib
import io
import json
import tarfile
import gzip
from pathlib import Path
from typing import Any

from . import __version__
from .data import AirportDataStore


def _canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_contract(contract_path: str | Path) -> dict[str, object]:
    path = Path(contract_path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_parser_help() -> str:
    # Local import avoids a module cycle at import time.
    from .cli import render_help_text

    return render_help_text()


def _build_smoke_expected(store: AirportDataStore, contract: dict[str, object]) -> dict[str, object]:
    smoke_cases = contract["smoke_cases"]
    assert isinstance(smoke_cases, list)
    expected: dict[str, object] = {}
    for case in smoke_cases:
        assert isinstance(case, dict)
        case_id = str(case["id"])
        args = case["args"]
        assert isinstance(args, list)
        if args == ["--help"]:
            stdout = _build_parser_help()
        elif args == ["version", "--format", "json"]:
            stdout = _canonical_json_bytes(
                {"package_name": str(contract["package_name"]), "version": str(contract["version"])}
            ).decode("utf-8")
        elif args == ["stats", "--format", "json"]:
            stdout = _canonical_json_bytes(store.stats()).decode("utf-8")
        elif len(args) == 4 and args[0] == "airport" and args[2:] == ["--format", "json"]:
            stdout = _canonical_json_bytes(store.get_airport(str(args[1]))).decode("utf-8")
        elif (
            len(args) == 6
            and args[0] == "country"
            and args[2] == "--limit"
            and args[4:] == ["--format", "json"]
        ):
            iso_country = str(args[1])
            limit = int(str(args[3]))
            airports = store.get_country_airports(iso_country, limit=limit)
            stdout = _canonical_json_bytes(
                {
                    "country_code": iso_country.strip().upper(),
                    "returned": len(airports),
                    "airports": airports,
                }
            ).decode("utf-8")
        else:
            raise ValueError(f"unsupported smoke case: {args}")

        expected[case_id] = {
            "args": args,
            "format": case["format"],
            "stdout": stdout,
        }
    return expected


def _build_command_catalog(contract: dict[str, object]) -> str:
    smoke_cases = contract["smoke_cases"]
    assert isinstance(smoke_cases, list)
    lines = [
        "# Airdesk Command Catalog",
        "",
        "## Build",
        "",
        "- `make help`",
        "- `make python-init`",
        "- `make python-tests`",
        "- `make cli-smoke-tests`",
        "- `make package`",
        "- `make packaged-smoke`",
        "- `make preview`",
        "- `make release`",
        "- `make check`",
        "- `make clean`",
        "",
        "## Smoke checks",
        "",
    ]
    for case in smoke_cases:
        assert isinstance(case, dict)
        command = "airdesk " + " ".join(str(part) for part in case["args"])
        lines.append(f"- `{command}`")
    lines.extend(
        [
            "",
            "## Examples",
            "",
            "- `airdesk version --format json`",
            "- `airdesk stats --format json`",
            "- `airdesk airport KJFK --format json`",
            "- `airdesk country US --limit 3 --format json`",
            "",
        ]
    )
    return "\n".join(lines)


def _build_launcher_script() -> bytes:
    script = """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${PACKAGE_ROOT}/lib${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m airdesk "$@"
"""
    return script.encode("utf-8")


def _artifact_file_map(contract: dict[str, object]) -> dict[str, bytes]:
    package_dir = f"{contract['package_name']}_{contract['version']}_linux_amd64"
    root = Path(__file__).resolve().parent
    file_map: dict[str, bytes] = {
        f"{package_dir}/bin/airdesk": _build_launcher_script(),
        f"{package_dir}/lib/airdesk/__init__.py": (root / "__init__.py").read_bytes(),
        f"{package_dir}/lib/airdesk/__main__.py": (root / "__main__.py").read_bytes(),
        f"{package_dir}/lib/airdesk/cli.py": (root / "cli.py").read_bytes(),
        f"{package_dir}/lib/airdesk/data.py": (root / "data.py").read_bytes(),
        f"{package_dir}/lib/airdesk/release.py": (root / "release.py").read_bytes(),
    }
    return file_map


def _require_release_prerequisites(require_package_lock: bool) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    required = [repo_root / "build" / "pydeps" / ".ready"]
    if require_package_lock:
        required.append(repo_root / "build" / "package.lock")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "missing release prerequisites: " + ", ".join(missing) + "; run make python-init first and run make package before final release generation"
        )


def _build_reproducible_tar_gz(contract: dict[str, object]) -> bytes:
    file_map = _artifact_file_map(contract)
    source_date_epoch = int(contract.get("source_date_epoch", 1_710_115_200))
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=source_date_epoch, filename="") as gz_file:
        with tarfile.open(fileobj=gz_file, mode="w") as tar:
            dirs: set[str] = set()
            for arcname in file_map:
                path = Path(arcname)
                for parent in path.parents:
                    if parent == Path("."):
                        continue
                    dirs.add(parent.as_posix())
            for dirname in sorted(dirs):
                info = tarfile.TarInfo(dirname)
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                info.mtime = source_date_epoch
                info.uid = 0
                info.gid = 0
                info.uname = "root"
                info.gname = "root"
                tar.addfile(info)
            for arcname in sorted(file_map):
                data = file_map[arcname]
                info = tarfile.TarInfo(arcname)
                info.size = len(data)
                info.mode = 0o755 if arcname.endswith("/bin/airdesk") else 0o644
                info.mtime = source_date_epoch
                info.uid = 0
                info.gid = 0
                info.uname = "root"
                info.gname = "root"
                tar.addfile(info, io.BytesIO(data))
    return output.getvalue()


def build_release(
    data_dir: str | Path,
    contract_path: str | Path,
    output_dir: str | Path,
    build_target: str,
    require_package_lock: bool = False,
) -> dict[str, object]:
    _require_release_prerequisites(require_package_lock=require_package_lock)
    store = AirportDataStore(data_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    contract = _load_contract(contract_path)
    source_files = contract["source_files"]
    assert isinstance(source_files, list)

    source_sha256: dict[str, str] = {}
    for filename in source_files:
        path = Path(data_dir) / str(filename)
        source_sha256[str(filename)] = _sha256_file(path)

    source_row_counts = store.row_counts()
    smoke_expected = _build_smoke_expected(store, contract)
    command_catalog = _build_command_catalog(contract)

    manifest = {
        "package_name": contract["package_name"],
        "version": contract["version"],
        "artifact_name": contract["artifact_name"],
        "entrypoint": contract["entrypoint"],
        "build_target": build_target,
        "source_files": source_files,
        "source_sha256": source_sha256,
        "source_row_counts": source_row_counts,
        "smoke_cases": contract["smoke_cases"],
    }

    manifest_path = output_root / "release_manifest.json"
    smoke_expected_path = output_root / "smoke_expected.json"
    command_catalog_path = output_root / "command_catalog.md"
    artifact_path = output_root / str(contract["artifact_name"])
    sha256_path = output_root / "sha256sums.txt"

    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    smoke_expected_path.write_bytes(_canonical_json_bytes(smoke_expected))
    command_catalog_path.write_text(command_catalog, encoding="utf-8")
    artifact_path.write_bytes(_build_reproducible_tar_gz(contract))

    sha_lines = [
        f"{_sha256_file(artifact_path)}  {artifact_path.name}",
        f"{_sha256_file(manifest_path)}  {manifest_path.name}",
        f"{_sha256_file(smoke_expected_path)}  {smoke_expected_path.name}",
    ]
    sha256_path.write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    return manifest
