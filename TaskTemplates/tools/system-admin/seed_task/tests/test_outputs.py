from __future__ import annotations

import hashlib
import json
import lzma
from pathlib import Path


APP_ROOT = Path("/app")
DATA_ROOT = APP_ROOT / "data"
RUNTIME_ROOT = APP_ROOT / "runtime"
OUTPUT_FILE = APP_ROOT / "output" / "recovery_report.json"
PUBLISHED_FILE = RUNTIME_ROOT / "published" / "bookworm-security-digest.json"
RECEIPT_FILE = RUNTIME_ROOT / "published" / "publish_receipt.json"
AUDIT_FILE = RUNTIME_ROOT / "logs" / "console_audit.jsonl"
STATE_FILE = RUNTIME_ROOT / "state" / "publisher_state.json"
CONTEXT_FILE = RUNTIME_ROOT / "state" / "console_recovery_context.json"
TRACKED_PACKAGES_FILE = DATA_ROOT / "incident" / "tracked_packages.json"
PACKAGES_XZ_FILE = DATA_ROOT / "upstream" / "Packages.xz"

EXPECTED_IMMUTABLE_HASHES = {
    DATA_ROOT / "upstream" / "InRelease": "dde39073e5912e2f71cb3947d91393e7408c292bf9019bf97a98d36f97927486",
    DATA_ROOT / "upstream" / "Packages.xz": "9313e46ae7290d95aa668027360c3fc9f0b4505c1c358fff91984e0d00ca1b72",
    APP_ROOT / "ops" / "recovery_console.py": "018256788e58a816ffd4e56de6b57aa626725e306744ba5c0b9c330f1bc007b6",
    APP_ROOT / "ops" / "digest_pipeline.py": "9060bcd8c239ec17ddbdab2e097ff6e38339c7fed7d06bf3f66c0dead805eba0",
    DATA_ROOT / "incident" / "incident_notes.md": "0025e53c3f2f976cb4ad620e87df80b84f7574df89d518311451a24af85666da",
    DATA_ROOT / "incident" / "tracked_packages.json": "95f22634b9f26007406682ccdb0a0d235978483bfe772f942b16760473dddbca",
    APP_ROOT / "bootstrap" / "bootstrap_staged_session.sh": "af52626a93886e5eee08d459efe092cf2adede0d5d091cdc0d569de72a7b027e",
    Path("/usr/local/bin/task-session-bootstrap"): "4e9a46b8c3a34e862aba6acf4b86cb2c148146bed2ee81cb2218839f8d5e3683",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def expected_report() -> dict:
    tracked = json.loads(TRACKED_PACKAGES_FILE.read_text(encoding="utf-8"))
    packages = parse_packages_xz(PACKAGES_XZ_FILE)
    versions: dict[str, str] = {}
    for stanza in packages:
        package = stanza.get("Package")
        if package in tracked and package not in versions:
            versions[package] = stanza["Version"]
    digest_payload = {
        "snapshot_id": "20240311T000000Z",
        "suite": "bookworm-security",
        "component": "main",
        "architecture": "amd64",
        "published": True,
        "package_count": len(packages),
        "tracked_packages": versions,
    }
    digest_bytes = (json.dumps(digest_payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest_sha256 = hashlib.sha256(digest_bytes).hexdigest()
    return {
        **digest_payload,
        "digest_sha256": digest_sha256,
    }


def load_audit() -> list[dict]:
    return [
        json.loads(line)
        for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_context() -> dict:
    return json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))


class TestMain:
    def test_output_exists_and_matches_expected(self) -> None:
        assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
        actual = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        assert actual == expected_report()

    def test_published_artifact_matches_report_hash(self) -> None:
        assert PUBLISHED_FILE.exists(), f"Missing published digest: {PUBLISHED_FILE}"
        report = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        digest_hash = sha256_file(PUBLISHED_FILE)
        assert report["digest_sha256"] == digest_hash

    def test_publish_receipt_consistent(self) -> None:
        assert RECEIPT_FILE.exists(), f"Missing publish receipt: {RECEIPT_FILE}"
        receipt = json.loads(RECEIPT_FILE.read_text(encoding="utf-8"))
        report = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        for key in report:
            assert receipt[key] == report[key]
        assert receipt["published_artifact"] == str(PUBLISHED_FILE)

    def test_audit_log_contains_real_recovery_sequence(self) -> None:
        audit = load_audit()
        assert audit, "Audit log is empty"
        context = load_context()
        staged_sid = context["staged_console_session_id"]

        rebuild_ok = [entry for entry in audit if entry["event"] == "rebuild_digest" and entry.get("result") == "ok"]
        assert len(rebuild_ok) == 1, "Expected exactly one successful staged rebuild"
        assert rebuild_ok[0]["session_id"] == staged_sid

        publish_ok = [entry for entry in audit if entry["event"] == "publish_digest" and entry.get("result") == "ok"]
        report_ok = [entry for entry in audit if entry["event"] == "write_report" and entry.get("result") == "ok"]
        assert publish_ok and publish_ok[-1]["session_id"] == staged_sid
        assert report_ok and report_ok[-1]["session_id"] == staged_sid

        staged_events = [entry["event"] for entry in audit if entry["session_id"] == staged_sid]
        required = ["session_start", "resume_pipeline", "clear_stale_lock", "rebuild_digest", "publish_digest", "write_report"]
        assert all(name in staged_events for name in required), "Staged live session did not complete the full recovery flow"


class TestGuardrails:
    def test_immutable_inputs_and_console_code_unchanged(self) -> None:
        for path, expected in EXPECTED_IMMUTABLE_HASHES.items():
            assert path.exists(), f"Missing immutable file: {path}"
            assert sha256_file(path) == expected, f"Immutable file changed: {path}"

    def test_runtime_state_is_healthy_after_publish(self) -> None:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        context = load_context()
        assert state["pipeline_mode"] == "active"
        assert state["stale_lock"] is False
        assert state["draft_ready"] is True
        assert state["published"] is True
        assert state["recovery_owner_session_id"] == context["staged_console_session_id"]

    def test_receipt_session_has_successful_publish_and_report(self) -> None:
        receipt = json.loads(RECEIPT_FILE.read_text(encoding="utf-8"))
        context = load_context()
        sid = receipt["session_id"]
        assert sid == context["staged_console_session_id"]
        events = [entry for entry in load_audit() if entry["session_id"] == sid]
        publish_events = [entry for entry in events if entry["event"] == "publish_digest"]
        report_events = [entry for entry in events if entry["event"] == "write_report"]
        assert publish_events and publish_events[-1]["result"] == "ok"
        assert report_events and report_events[-1]["result"] == "ok"
