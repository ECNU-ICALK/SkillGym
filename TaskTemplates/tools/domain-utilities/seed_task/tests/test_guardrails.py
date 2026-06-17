from __future__ import annotations

import hashlib
import os
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/workspace/data"))
SOURCE_HASH_PATH = Path(os.environ.get("SOURCE_HASH_PATH", "/opt/domain-source-bundle.sha256"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw_hash, raw_path = line.split("  ", 1)
        hashes[Path(raw_path).name] = raw_hash
    return hashes


def test_input_bundle_hashes_unchanged() -> None:
    expected = recorded_hashes(SOURCE_HASH_PATH)
    for file_path in DATA_DIR.iterdir():
        if file_path.is_file():
            assert digest(file_path) == expected[file_path.name], f"input file changed: {file_path.name}"


def test_only_required_output_files_exist() -> None:
    files = sorted(path.name for path in OUTPUT_DIR.iterdir() if path.is_file())
    assert files == ["availability_audit.csv", "domain_shortlist.json"]
