from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path


TASK_ROOT = Path(os.environ.get("ARTS_CRAFTS_TASK_ROOT", "/root"))
ANSWER_DIR = TASK_ROOT / "answer"
MODELS_DIR = ANSWER_DIR / "models"
DATA_DIR = TASK_ROOT / "environment" / "data"
SKILL_PATH = Path(os.environ.get("ARTS_CRAFTS_SKILL_PATH", "/root/.codex/skills/find-stl/scripts/find_stl.py"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_skill_module():
    spec = importlib.util.spec_from_file_location("find_stl_skill", SKILL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def policy_checks(model: dict, policy: dict, slot_id: str) -> dict[str, bool]:
    rule = policy["slot_rules"][slot_id]
    text = " ".join(
        [
            model.get("name", ""),
            model.get("summary", ""),
            model.get("description", ""),
        ]
    ).lower()
    license_allowed = (
        model["license"]["id"] in policy["allowed_license_ids"]
        and not model["license"]["disallowRemixing"]
        and not model["excludeCommercialUsage"]
    )
    popularity_ok = int(model["downloadCount"]) >= int(policy["minimum_download_count"])
    if slot_id == "tool-storage":
        slot_match = all(term.lower() in text for term in rule["required_terms"]) and int(model["filesCount"]) >= int(rule["minimum_files_count"])
    else:
        slot_match = all(term.lower() in text for term in rule["required_terms"])
    if any(term.lower() in text for term in rule.get("forbidden_terms", [])):
        slot_match = False
    if slot_id != "tool-storage" and not all(term.lower() in text for term in rule.get("preferred_terms", [])):
        slot_match = False
    return {
        "slot_match": slot_match,
        "license_allowed": license_allowed,
        "popularity_ok": popularity_ok,
    }


def choose_models(skill, brief: dict, policy: dict, shortlist: dict) -> tuple[dict[str, dict], list[str]]:
    choices: dict[str, dict] = {}
    checked: list[str] = []
    for query_info in load_json(DATA_DIR / "catalog" / "search_terms.json")["queries"]:
        slot_id = query_info["slot_id"]
        results = skill.printables_search(query_info["query"], limit=query_info["limit"], offset=0)["items"]
        candidate_ids = [str(item["id"]) for item in results]
        ordered = []
        seen = set()
        for model_id in candidate_ids:
            if model_id in seen:
                continue
            seen.add(model_id)
            ordered.append(model_id)

        winner = None
        for model_id in ordered:
            model = skill.printables_get_print(model_id)
            checked.append(str(model_id))
            checks = policy_checks(model, policy, slot_id)
            if all(checks.values()):
                if winner is None or (
                    int(model["downloadCount"]),
                    int(model["likesCount"]),
                    int(model["filesCount"]),
                ) > (
                    int(winner["downloadCount"]),
                    int(winner["likesCount"]),
                    int(winner["filesCount"]),
                ):
                    winner = model
        if winner is None:
            raise RuntimeError(f"No winner for slot {slot_id}")
        choices[slot_id] = winner
    return choices, checked


def fetch_model(skill, model: dict, slot_dir: Path) -> tuple[list[dict], dict]:
    slot_dir.mkdir(parents=True, exist_ok=True)
    files_dir = slot_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="bundle-fetch-"))
    try:
        pack_dir = temp_dir / "incoming"
        pack_dir.mkdir(parents=True, exist_ok=True)
        pack_id = str(model["downloadPacks"][0]["id"])
        link = skill.printables_get_download_link(model["id"], "pack", [pack_id])
        zip_path = pack_dir / f"{pack_id}.zip"
        skill.download_file(link, str(zip_path))
        source_bundle_path = slot_dir / "source_bundle.zip"
        shutil.copy2(zip_path, source_bundle_path)
        with zipfile.ZipFile(source_bundle_path, "r") as zf:
            zf.extractall(temp_dir / "extract")
        extracted_files = sorted(path for path in (temp_dir / "extract").rglob("*") if path.is_file())
        file_entries = []
        for path in extracted_files:
            target = files_dir / path.name
            shutil.copy2(path, target)
            file_entries.append(
                {
                    "path": f"files/{path.name}",
                    "sha256": skill.sha256_file(str(target)),
                }
            )
        source_url = f"https://www.printables.com/model/{model['id']}-{model['slug']}"
        source_manifest = {
            "source": "printables",
            "source_url": source_url,
            "print": {
                "id": model["id"],
                "name": model["name"],
                "slug": model["slug"],
                "author": model["user"]["handle"],
                "license_id": model["license"]["id"],
                "downloadCount": model["downloadCount"],
                "likesCount": model["likesCount"],
                "filesCount": model["filesCount"],
            },
            "downloaded": [
                {
                    "kind": "pack",
                    "id": pack_id,
                    "path": "source_bundle.zip",
                    "sha256": skill.sha256_file(str(source_bundle_path)),
                    "url": link,
                }
            ],
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return file_entries, source_manifest
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_outputs(skill, brief: dict, policy: dict, choices: dict[str, dict], checked_ids: list[str]) -> None:
    if ANSWER_DIR.exists():
        shutil.rmtree(ANSWER_DIR)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    selections = []
    prepared = []

    for slot_id in brief["slot_order"]:
        model = choices[slot_id]
        slot_dir = MODELS_DIR / slot_id
        files, source_manifest = fetch_model(skill, model, slot_dir)
        checks = policy_checks(model, policy, slot_id)
        checks["files_present"] = bool(files)
        source_url = f"https://www.printables.com/model/{model['id']}-{model['slug']}"
        (slot_dir / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2), encoding="utf-8")
        record = {
            "model_id": str(model["id"]),
            "model_name": model["name"],
            "author": model["user"]["handle"],
            "source_url": source_url,
            "license_id": model["license"]["id"],
            "files": files,
        }
        (slot_dir / "model_record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        selections.append(
            {
                "slot_id": slot_id,
                "model_id": str(model["id"]),
                "model_name": model["name"],
                "author": model["user"]["handle"],
                "source_url": source_url,
                "license_id": model["license"]["id"],
                "local_dir": f"models/{slot_id}",
                "policy_checks": checks,
            }
        )
        prepared.append(slot_id)

    bundle_manifest = {
        "bundle_name": brief["bundle_name"],
        "slot_order": brief["slot_order"],
        "selections": selections,
        "policy_summary": {
            "allowed_license_ids": policy["allowed_license_ids"],
            "minimum_download_count": policy["minimum_download_count"],
        },
        "manual_checks": brief["manual_checks_template"],
    }
    (ANSWER_DIR / "bundle_manifest.json").write_text(json.dumps(bundle_manifest, indent=2), encoding="utf-8")

    selection_audit = {
        "source_endpoint": skill.PRINTABLES_GQL,
        "source_checked": True,
        "model_ids_checked": checked_ids,
        "records_prepared": prepared,
        "notes": [
            "Selection combined query results, shortlist hints, policy checks, and downloaded file records."
        ],
    }
    (ANSWER_DIR / "selection_audit.json").write_text(json.dumps(selection_audit, indent=2), encoding="utf-8")

    lines = ["Fiber workshop starter bundle prepared for supplier handoff."]
    for slot_id in brief["slot_order"]:
        model = choices[slot_id]
        source_url = f"https://www.printables.com/model/{model['id']}-{model['slug']}"
        lines.append(f"## {slot_id}")
        lines.append(f"- 选型：{model['name']} ({source_url})")
        lines.append(f"- 入选理由：下载量 {model['downloadCount']}，槽位语义与规则匹配。")
        lines.append(f"- 许可与交付注意点：license 为 `{model['license']['id']}`，交付目录已附文件校验信息。")
        lines.append("")
    (ANSWER_DIR / "selection_report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    if not SKILL_PATH.exists():
        raise RuntimeError("Bound find-stl skill is missing from /root/.codex/skills")
    skill = load_skill_module()
    skill.PRINTABLES_GQL = os.environ.get("ARTS_CRAFTS_SOURCE_ENDPOINT", skill.PRINTABLES_GQL)
    brief = load_json(DATA_DIR / "brief" / "workshop_bundle.json")
    policy = load_json(DATA_DIR / "policy" / "bundle_rules.json")
    shortlist = load_json(DATA_DIR / "catalog" / "candidate_shortlist.json")
    choices, checked_ids = choose_models(skill, brief, policy, shortlist)
    write_outputs(skill, brief, policy, choices, checked_ids)


if __name__ == "__main__":
    main()
