#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import lzma
from pathlib import Path

SNAPSHOT_ID = "20240311T000000Z"
SUITE = "bookworm-security"
COMPONENT = "main"
ARCHITECTURE = "amd64"


def parse_packages_xz(path: Path) -> list[dict[str, str]]:
    text = lzma.decompress(path.read_bytes()).decode("utf-8", "replace")
    stanzas: list[dict[str, str]] = []
    for block in text.strip().split("\n\n"):
        stanza: dict[str, str] = {}
        current_key: str | None = None
        for line in block.splitlines():
            if not line:
                continue
            if line.startswith(" ") and current_key:
                stanza[current_key] = stanza[current_key] + "\n" + line[1:]
                continue
            if ": " not in line:
                continue
            key, value = line.split(": ", 1)
            stanza[key] = value
            current_key = key
        if stanza:
            stanzas.append(stanza)
    return stanzas


def build_digest(upstream_dir: Path, tracked_packages_path: Path) -> dict:
    packages = parse_packages_xz(upstream_dir / "Packages.xz")
    tracked = json.loads(tracked_packages_path.read_text(encoding="utf-8"))
    tracked_versions: dict[str, str] = {}

    for stanza in packages:
        package = stanza.get("Package")
        if package in tracked and package not in tracked_versions:
            tracked_versions[package] = stanza["Version"]

    missing = [package for package in tracked if package not in tracked_versions]
    if missing:
        raise RuntimeError(f"Missing tracked packages: {missing}")

    digest = {
        "snapshot_id": SNAPSHOT_ID,
        "suite": SUITE,
        "component": COMPONENT,
        "architecture": ARCHITECTURE,
        "published": True,
        "package_count": len(packages),
        "tracked_packages": tracked_versions,
    }
    return digest


def canonical_json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def report_from_digest(digest: dict, digest_sha256: str) -> dict:
    report = dict(digest)
    report["digest_sha256"] = digest_sha256
    return report
