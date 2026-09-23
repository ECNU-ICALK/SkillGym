from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
EXTENSION_ROOT = WORKSPACE_ROOT / "extension"
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
INPUT_HASH_RECORD = Path(os.environ.get("INPUT_HASH_RECORD", "/opt/release-briefing-inputs.sha256"))
SUPPORTED_LOCALES = ["en", "pt-br", "zh-cn"]


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_input_hashes_match_build_record() -> None:
    expected = {}
    for line in INPUT_HASH_RECORD.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, file_path = line.split(maxsplit=1)
        expected[file_path] = digest

    for file_path, digest in expected.items():
        actual = sha256_bytes(Path(file_path))
        assert actual == digest, f"input file changed: {file_path}"


def test_locale_copy_schema_matches_manifest_tokens() -> None:
    manifest = read_json(EXTENSION_ROOT / "package.json")
    token_keys: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, str):
            token_keys.update(token[1:-1] for token in re.findall(r"%[^%]+%", value))
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    walk(manifest)
    for locale in SUPPORTED_LOCALES:
        payload = read_json(DATA_ROOT / "locales" / locale / "extension_copy.json")
        package_copy = payload["package"]
        for key in token_keys:
            assert package_copy.get(key), f"missing manifest token {key} in {locale} locale copy"

        for key, section_name in [
            ("walkthrough.step.browse.markdown", "browse"),
            ("walkthrough.step.export.markdown", "export"),
            ("walkthrough.step.package.markdown", "package"),
        ]:
            relative = package_copy[key]
            assert relative.startswith(f"./resources/walkthrough/{locale}/"), (
                f"{locale} walkthrough path should stay in its locale directory"
            )
            assert payload["walkthrough"].get(section_name), f"missing walkthrough copy for {locale}:{section_name}"


def test_locale_copy_bundles_cover_runtime_strings() -> None:
    extension_source = (EXTENSION_ROOT / "src" / "extension.js").read_text(encoding="utf-8")
    core_source = (EXTENSION_ROOT / "src" / "core.js").read_text(encoding="utf-8")
    english_bundle = read_json(DATA_ROOT / "locales" / "en" / "extension_copy.json")["bundle"]
    runtime_keys = set(re.findall(r'vscode\.l10n\.t\(\s*"([^"]+)"', extension_source))
    runtime_keys.update(re.findall(r'bundle\["([^"]+)"\]', core_source))

    assert runtime_keys <= set(english_bundle), "english locale copy is missing runtime strings used in source"
    assert not re.search(r'bundle\["briefing\.[^"]+"\]', core_source), (
        "runtime bundle lookups should use English source-string keys"
    )

    english_keys = set(english_bundle)
    for locale in ["pt-br", "zh-cn"]:
        localized_keys = set(read_json(DATA_ROOT / "locales" / locale / "extension_copy.json")["bundle"])
        assert localized_keys == english_keys, f"{locale} runtime bundle keys differ from english locale copy"
