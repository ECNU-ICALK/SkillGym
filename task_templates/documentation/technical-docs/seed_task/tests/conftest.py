from __future__ import annotations

import html
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_ROOT = Path("/environment/reference_bundle")
DEFAULT_WORKSPACE_ROOT = Path("/environment/workspace")
DEFAULT_OUTPUT_ROOT = Path("/environment/output")
LOCAL_BUNDLE_ROOT = TASK_ROOT / "environment" / "reference_bundle"
LOCAL_WORKSPACE_ROOT = TASK_ROOT / "environment" / "workspace"
LOCAL_OUTPUT_ROOT = TASK_ROOT / ".tmp_test_output"


def running_inside_task_runtime() -> bool:
    return TASK_ROOT == Path("/environment")


def choose_root(env_name: str, runtime_root: Path, local_root: Path) -> Path:
    if env_name in os.environ:
        return Path(os.environ[env_name])
    if running_inside_task_runtime():
        return runtime_root
    if local_root.exists():
        return local_root
    return runtime_root


BUNDLE_ROOT = choose_root("TASK_BUNDLE_ROOT", DEFAULT_BUNDLE_ROOT, LOCAL_BUNDLE_ROOT)
WORKSPACE_ROOT = choose_root("TASK_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT, LOCAL_WORKSPACE_ROOT)
OUTPUT_ROOT = Path(os.environ["TASK_OUTPUT_ROOT"]) if "TASK_OUTPUT_ROOT" in os.environ else (
    DEFAULT_OUTPUT_ROOT if running_inside_task_runtime() else LOCAL_OUTPUT_ROOT
)

BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_reference.py"
SKILL_ROOT = TASK_ROOT / "environment" / "skills" / "write-api-reference"
EMPTY_SHA256_FILE = hashlib.sha256(b"").hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_build(bundle_root: Path = BUNDLE_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--bundle-root",
            str(bundle_root),
            "--workspace-root",
            str(WORKSPACE_ROOT),
            "--output-root",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        cwd=WORKSPACE_ROOT,
    )


def contract(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(bundle_root / "contracts" / "page_contract.json")


def rules(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(bundle_root / "contracts" / "reference_rules.json")


def package_metadata(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(bundle_root / "upstream" / "package.json")


def version_notes(bundle_root: Path = BUNDLE_ROOT) -> list[dict[str, str]]:
    return load_json(bundle_root / "contracts" / "version_notes.json")["entries"]


def output_page(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["output_file"]


def output_manifest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["manifest_file"]


def read_page(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> str:
    return output_page(output_root, bundle_root).read_text(encoding="utf-8")


def read_manifest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(output_manifest(output_root, bundle_root))


def parse_frontmatter(page_text: str) -> tuple[dict[str, str], str]:
    lines = page_text.splitlines()
    assert lines and lines[0] == "---", "missing opening frontmatter fence"
    end = lines.index("---", 1)
    frontmatter: dict[str, str] = {}
    for line in lines[1:end]:
        key, value = line.split(":", 1)
        normalized = value.strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
            normalized = normalized[1:-1]
        frontmatter[key.strip()] = normalized
    body = "\n".join(lines[end + 1 :]).strip() + "\n"
    return frontmatter, body


def normalize(text: str) -> str:
    return " ".join(text.split())


def directory_listing(root: Path) -> str:
    if not root.exists():
        return ""
    lines: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + ("\n" if lines else "")


def normalize_listing_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, _, rel_path = line.partition("  ")
        lines.append(f"{digest}  {rel_path.removeprefix('./')}")
    return "\n".join(lines) + ("\n" if lines else "")


def baseline_reference_listing() -> str:
    baseline_path = Path("/opt/task-baselines/reference-bundle.sha256")
    if baseline_path.exists():
        return normalize_listing_text(baseline_path.read_text(encoding="utf-8"))
    return directory_listing(BUNDLE_ROOT)


def expected_documented_api_names(bundle_root: Path = BUNDLE_ROOT) -> list[tuple[str, str]]:
    payload = contract(bundle_root)
    pairs: list[tuple[str, str]] = [(payload["constructor"]["signature"], "constructor")]
    pairs.extend((item["name"], "option") for item in payload["queue_options"])
    pairs.extend((item["name"], "option") for item in payload["task_options"])
    pairs.extend((item["name"], item["kind"]) for item in payload["methods"])
    pairs.extend((item["name"], item["kind"]) for item in payload["properties"])
    pairs.extend((item["name"], item["kind"]) for item in payload["events"])
    return pairs


def extract_release_highlight(release_html: str) -> str:
    matches = re.findall(r"<li>(.*?)</li>", release_html, flags=re.DOTALL)
    for match in matches:
        if "intervalCount" not in match:
            continue
        text = re.sub(r"<[^>]+>", "", match)
        text = html.unescape(" ".join(text.split()))
        if text:
            return text
    raise AssertionError("unable to find release highlight")


def extract_id_assigner_start(source_text: str) -> str:
    match = re.search(r"#idAssigner\s*=\s*(\d+)n;", source_text)
    assert match, "missing #idAssigner assignment"
    return f"{match.group(1)}n"


def extract_sizeby_priority_expectations(test_text: str) -> list[tuple[str, str]]:
    block_match = re.search(
        r"test\('\.sizeBy\(\) - priority'.*?\n\}\);",
        test_text,
        flags=re.DOTALL,
    )
    assert block_match, "missing sizeBy priority test block"
    block = block_match.group(0)
    pairs = re.findall(r"sizeBy\(\{priority: ([^}]+)\}\), (\d+)", block)
    assert pairs, "missing sizeBy expectations"
    return pairs


def extract_timeout_update_values(test_text: str) -> tuple[str, str]:
    block_match = re.search(
        r"test\('\.add\(\) - change timeout in between'.*?\n\}\);",
        test_text,
        flags=re.DOTALL,
    )
    assert block_match, "missing timeout change test block"
    block = block_match.group(0)
    initial = re.search(r"initialTimeout = (\d+);", block)
    updated = re.search(r"newTimeout = (\d+);", block)
    assert initial and updated, "missing timeout values"
    return initial.group(1), updated.group(1)


def make_alternate_bundle_copy() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory(prefix="pqueue-alt-bundle-")
    alt_root = Path(tmpdir.name) / "reference_bundle"
    shutil.copytree(BUNDLE_ROOT, alt_root)

    package = package_metadata(alt_root)
    package["description"] = "Promise queue with interval-aware backpressure for alternate fixture verification"
    (alt_root / "upstream" / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    release_html = (alt_root / "upstream" / "release_v8.1.1.html").read_text(encoding="utf-8")
    release_html = release_html.replace(
        "Don't count aborted jobs in intervalCount (#220) 199614e",
        "Skip aborted jobs when interval counters roll over (#220) alt199614e",
        1,
    )
    (alt_root / "upstream" / "release_v8.1.1.html").write_text(release_html, encoding="utf-8")

    source_index = (alt_root / "upstream" / "source" / "index.ts").read_text(encoding="utf-8")
    source_index = source_index.replace("#idAssigner = 1n;", "#idAssigner = 41n;", 1)
    (alt_root / "upstream" / "source" / "index.ts").write_text(source_index, encoding="utf-8")

    source_tests = (alt_root / "upstream" / "test" / "test.ts").read_text(encoding="utf-8")
    source_tests = source_tests.replace("sizeBy({priority: 1}), 2", "sizeBy({priority: 4}), 3", 1)
    source_tests = source_tests.replace("sizeBy({priority: 0}), 1", "sizeBy({priority: 2}), 1", 1)
    source_tests = source_tests.replace("sizeBy({priority: 1}), 0", "sizeBy({priority: 4}), 0", 1)
    source_tests = source_tests.replace("sizeBy({priority: 0}), 0", "sizeBy({priority: 2}), 0", 1)
    source_tests = source_tests.replace("initialTimeout = 50;", "initialTimeout = 75;", 1)
    source_tests = source_tests.replace("newTimeout = 200;", "newTimeout = 275;", 1)
    (alt_root / "upstream" / "test" / "test.ts").write_text(source_tests, encoding="utf-8")

    payload = contract(alt_root)
    payload["required_examples"][2]["title"] = "Cancel queued work after a controller abort"
    payload["behavior_notes"][0]["text"] = "Greater `priority` values still schedule before lower values in the alternate fixture."
    (alt_root / "contracts" / "page_contract.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    notes = version_notes(alt_root)
    notes[0]["summary"] = "Alternate fixture version note for the bundled release snapshot."
    (alt_root / "contracts" / "version_notes.json").write_text(json.dumps({"entries": notes}, indent=2) + "\n", encoding="utf-8")
    return tmpdir, alt_root
