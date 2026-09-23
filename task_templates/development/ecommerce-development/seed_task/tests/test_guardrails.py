from __future__ import annotations

import hashlib
import os
from pathlib import Path

from oracle import DATA_ROOT, WP_PATH, request_json, run_cmd


REFERENCE_SHA_PATH = Path("/opt/printshop-data.sha256")


def compute_data_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(DATA_ROOT.glob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[path.name] = digest
    return hashes


def load_reference_hashes() -> dict[str, str]:
    if not REFERENCE_SHA_PATH.exists():
        raise AssertionError(f"missing reference hash file: {REFERENCE_SHA_PATH}")
    out: dict[str, str] = {}
    for line in REFERENCE_SHA_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, path = line.split(maxsplit=1)
        name = Path(path).name
        out[name] = digest
    return out


def assert_data_integrity() -> None:
    expected = load_reference_hashes()
    actual = compute_data_hashes()
    if expected.keys() != actual.keys():
        raise AssertionError(f"data file set changed: expected={sorted(expected)} actual={sorted(actual)}")
    diffs = {name: (actual[name], expected[name]) for name in actual if actual[name] != expected[name]}
    if diffs:
        raise AssertionError(f"input data hash mismatch: {diffs}")


def assert_site_health() -> None:
    status, payload = request_json("/wp-json/")
    if status != 200:
        raise AssertionError(f"wp-json health failed: status={status} payload={payload}")

    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed")
    if status != 200:
        raise AssertionError(f"launch-feed health failed: status={status} payload={payload}")

    plugin_list = run_cmd(
        ["wp", "plugin", "list", "--status=active", "--field=name", "--allow-root", f"--path={WP_PATH}"],
        check=True,
    )
    active = {line.strip() for line in plugin_list.stdout.splitlines() if line.strip()}
    required = {"woocommerce", "harbor-printshop"}
    if not required.issubset(active):
        raise AssertionError(f"plugins not active as expected, active={sorted(active)}")


def main() -> None:
    assert_data_integrity()
    assert_site_health()
    print("PASS")


if __name__ == "__main__":
    main()
