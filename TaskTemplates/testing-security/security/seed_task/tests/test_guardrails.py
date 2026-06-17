from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from common import DATA_ROOT, TASK_ROOT, build_alternate_fixture, request_json, request_text, running_server


FULL_KEY = "pk_live_emerald"


def _full_data_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.iterdir()):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_static_input_data_unchanged() -> None:
    assert _full_data_hash(DATA_ROOT) == "772d99ed8a90a5a50b794c468a508d2ba9f8fc81961bbf945eb423bbae541e94"


def test_behavior_generalizes_on_alternate_fixture() -> None:
    alt_data_dir, alt_state_dir = build_alternate_fixture()
    try:
        with running_server(data_dir=alt_data_dir, state_dir=alt_state_dir) as base_url:
            status, _, payload = request_json(
                base_url,
                "GET",
                "/api/v1/advisories?page=1&page_size=2&sort=-epss",
                api_key=FULL_KEY,
            )
            assert status == 200, payload
            assert [row["cve_id"] for row in payload["data"]] == ["CVE-2099-0001", "CVE-2024-23897"]

            create_status, _, create_payload = request_json(
                base_url,
                "POST",
                "/api/v1/export-jobs",
                api_key=FULL_KEY,
                payload={"filters": {"vendor": "progress", "severity": "high"}, "format": "csv"},
            )
            assert create_status == 201, create_payload
            job = create_payload["data"]

            download_status, _, csv_text = request_text(
                base_url,
                "GET",
                f"/api/v1/export-jobs/{job['id']}/download",
                api_key=FULL_KEY,
            )
            assert download_status == 200, csv_text
            assert "CVE-2099-0001" in csv_text
    finally:
        shutil.rmtree(alt_data_dir.parent)


def test_task_kept_expected_structure() -> None:
    assert Path("/app/workspace/server.js").exists() or (TASK_ROOT / "workspace" / "server.js").exists()
    assert Path("/app/workspace/service").exists() or (TASK_ROOT / "workspace" / "service").exists()
    assert Path("/tests/test.sh").exists() or (TASK_ROOT.parent / "tests" / "test.sh").exists()


def test_no_embedded_export_secret_fallback() -> None:
    app_path = Path("/app/workspace/service/app.js")
    if not app_path.exists():
        app_path = TASK_ROOT / "workspace" / "service" / "app.js"
    source = app_path.read_text(encoding="utf-8")
    assert "unsafe-dev-export-signing-secret" not in source
