from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

from test_helpers import (
    AUDIT_PATH,
    BUNDLE_PATH,
    MIRROR_ROOT,
    MODELS_DIR,
    OUTPUT_DIR,
    REPORT_PATH,
    load_json,
    seed_models,
    selected_models_from_policy,
    sha256,
)


def normalize_prepared_slot(entry: object) -> str:
    if isinstance(entry, str):
        path = Path(entry)
        if path.name == "model_record.json" and len(path.parts) >= 2:
            return path.parent.name
        if path.name in {"yarn-management", "stitch-marker", "tool-storage"}:
            return path.name
        if entry in {"yarn-management", "stitch-marker", "tool-storage"}:
            return entry
        raise AssertionError(f"Unexpected records_prepared entry: {entry!r}")
    if isinstance(entry, dict) and "slot_id" in entry:
        return str(entry["slot_id"])
    raise AssertionError(f"Unexpected records_prepared entry: {entry!r}")


def manifest_source_url(source_manifest: dict) -> str:
    return source_manifest.get("source_url") or source_manifest.get("source_page") or ""


def manifest_author_handle(source_manifest: dict) -> str:
    author = source_manifest.get("author")
    if isinstance(author, dict):
        return str(author.get("handle", ""))
    if author:
        return str(author)
    print_block = source_manifest.get("print")
    if isinstance(print_block, dict):
        return str(print_block.get("author", ""))
    return ""


def manifest_license_id(source_manifest: dict) -> str:
    if "license_id" in source_manifest:
        return str(source_manifest["license_id"])
    print_block = source_manifest.get("print")
    if isinstance(print_block, dict) and "license_id" in print_block:
        return str(print_block.get("license_id", ""))
    license_block = source_manifest.get("license", {})
    if isinstance(license_block, dict):
        return str(license_block.get("id", ""))
    return ""


def manifest_model_id(source_manifest: dict) -> str:
    print_block = source_manifest.get("print")
    if isinstance(print_block, dict) and "id" in print_block:
        return str(print_block["id"])
    return str(source_manifest.get("model_id", ""))


def manifest_downloaded(source_manifest: dict) -> list[dict]:
    downloaded = source_manifest.get("downloaded")
    if isinstance(downloaded, list) and downloaded:
        return downloaded
    source_bundle = source_manifest.get("source_bundle")
    if isinstance(source_bundle, dict):
        return [
            {
                "kind": "pack",
                "path": source_bundle.get("path", "source_bundle.zip"),
                "sha256": source_bundle.get("sha256"),
                "url": source_bundle.get("source_download_url") or source_bundle.get("download_url"),
            }
        ]
    return []


def test_required_outputs_exist() -> None:
    assert OUTPUT_DIR.exists(), "/root/answer was not created"
    assert MODELS_DIR.exists(), "models directory is missing"
    assert BUNDLE_PATH.exists(), "bundle_manifest.json is missing"
    assert AUDIT_PATH.exists(), "selection_audit.json is missing"
    assert REPORT_PATH.exists(), "selection_report.md is missing"


def test_slot_directories_and_model_records() -> None:
    bundle = load_json(BUNDLE_PATH)
    slots = bundle["slot_order"]
    assert slots == ["yarn-management", "stitch-marker", "tool-storage"]
    actual_dirs = sorted(path.name for path in MODELS_DIR.iterdir() if path.is_dir())
    assert actual_dirs == sorted(slots), f"Unexpected slot directories: {actual_dirs}"

    for slot in slots:
        slot_dir = MODELS_DIR / slot
        files_dir = slot_dir / "files"
        record_path = slot_dir / "model_record.json"
        source_manifest_path = slot_dir / "source_manifest.json"
        source_bundle_path = slot_dir / "source_bundle.zip"
        assert record_path.exists(), f"{slot} model_record.json is missing"
        assert source_manifest_path.exists(), f"{slot} source_manifest.json is missing"
        assert source_bundle_path.exists(), f"{slot} source_bundle.zip is missing"
        assert files_dir.exists() and files_dir.is_dir(), f"{slot} files directory is missing"
        record = load_json(record_path)
        for key in ["model_id", "model_name", "author", "source_url", "license_id", "files"]:
            assert key in record, f"{slot} record missing key {key}"
        assert isinstance(record["files"], list) and record["files"], f"{slot} record files list is empty"
        for file_info in record["files"]:
            assert "path" in file_info and "sha256" in file_info, f"{slot} file record is incomplete"
            payload_path = slot_dir / file_info["path"]
            assert payload_path.exists(), f"Missing payload file {payload_path}"
            assert sha256(payload_path) == file_info["sha256"], f"Checksum mismatch for {payload_path}"


def test_expected_model_selection_and_policy_checks() -> None:
    bundle = load_json(BUNDLE_PATH)
    records = {entry["slot_id"]: entry for entry in bundle["selections"]}
    expected = selected_models_from_policy()
    for slot, model in expected.items():
        assert slot in records, f"Selection missing slot {slot}"
        entry = records[slot]
        assert str(entry["model_id"]) == str(model["id"]), f"Wrong model chosen for {slot}"
        assert entry["model_name"] == model["name"], f"Wrong model name for {slot}"
        assert entry["author"] == model["user"]["handle"], f"Wrong author for {slot}"
        assert entry["license_id"] == model["license"]["id"], f"Wrong license for {slot}"
        checks = entry["policy_checks"]
        assert checks["slot_match"] is True
        assert checks["license_allowed"] is True
        assert checks["popularity_ok"] is True
        assert checks["files_present"] is True


def test_bundle_manifest_and_audit_contract() -> None:
    bundle = load_json(BUNDLE_PATH)
    audit = load_json(AUDIT_PATH)
    for key in ["bundle_name", "slot_order", "selections", "policy_summary", "manual_checks"]:
        assert key in bundle, f"bundle_manifest missing {key}"
    assert bundle["bundle_name"] == "fiber-workshop-starter-bundle"
    assert len(bundle["selections"]) == 3
    assert isinstance(bundle["manual_checks"], list) and bundle["manual_checks"], "manual_checks is empty"

    for key in ["source_endpoint", "source_checked", "model_ids_checked", "records_prepared", "notes"]:
        assert key in audit, f"selection_audit missing {key}"
    endpoint_text = str(audit["source_endpoint"])
    assert "graphql" in endpoint_text.lower(), f"Unexpected source endpoint text: {audit['source_endpoint']}"
    endpoint = urllib.parse.urlparse(endpoint_text)
    if endpoint.hostname:
        assert endpoint.hostname in {"api.printables.com", "127.0.0.1", "localhost"}, (
            f"Unexpected source endpoint host: {audit['source_endpoint']}"
        )
    assert audit["source_checked"] is True
    prepared = audit["records_prepared"]
    normalized_slots = [normalize_prepared_slot(item) for item in prepared]
    assert sorted(normalized_slots) == ["stitch-marker", "tool-storage", "yarn-management"]


def test_source_bundle_and_manifest_match_seed() -> None:
    expected = selected_models_from_policy()
    models = seed_models()
    for slot, model in expected.items():
        slot_dir = MODELS_DIR / slot
        source_manifest = load_json(slot_dir / "source_manifest.json")
        record = load_json(slot_dir / "model_record.json")
        seed_model = models[str(model["id"])]
        source_name = source_manifest.get("source")
        if source_name is None:
            source_name = "printables" if manifest_source_url(source_manifest) else None
        assert source_name == "printables"
        assert manifest_source_url(source_manifest) == record["source_url"]
        assert manifest_model_id(source_manifest) == str(seed_model["id"])
        assert manifest_author_handle(source_manifest) == seed_model["user"]["handle"]
        assert manifest_license_id(source_manifest) == seed_model["license"]["id"]
        downloaded = manifest_downloaded(source_manifest)
        assert downloaded, f"{slot} source manifest downloaded list is empty"
        assert downloaded[0]["kind"] == "pack", f"{slot} source manifest does not preserve the original pack"
        assert Path(downloaded[0]["path"]).name == "source_bundle.zip"

        mirror_pack = MIRROR_ROOT / "packs" / f"{seed_model['pack']['id']}.zip"
        assert mirror_pack.exists(), f"Missing mirrored pack for {slot}"
        assert sha256(slot_dir / "source_bundle.zip") == sha256(mirror_pack), f"Wrong source bundle for {slot}"


def test_report_structure() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert text.splitlines()[0].strip(), "selection_report first line is empty"
    for header in ["## yarn-management", "## stitch-marker", "## tool-storage"]:
        assert header in text, f"selection_report missing section {header}"


def test_downloaded_files_match_seed_names() -> None:
    expected = selected_models_from_policy()
    models = seed_models()
    for slot, model in expected.items():
        record = load_json(MODELS_DIR / slot / "model_record.json")
        expected_names = sorted(file_info["name"] for file_info in models[str(model["id"])]["files"])
        actual_names = sorted(
            Path(file_info["path"]).name
            for file_info in record["files"]
            if Path(file_info["path"]).suffix.lower() in {".stl", ".3mf", ".obj"}
        )
        assert actual_names == expected_names, f"Wrong model file set for {slot}"
        for file_info in record["files"]:
            assert Path(file_info["path"]).parts[0] == "files", f"{slot} model payload path must stay under files/"
