#!/usr/bin/env python3
import copy
import json
import os
from pathlib import Path

import yaml


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def default_data_root(repo_root: Path) -> Path:
    sibling = repo_root.parents[1] / "data"
    if sibling.exists():
        return sibling
    return Path("/app/data")


def main() -> None:
    target = os.environ.get("SATURN_TARGET_ENV") or (os.sys.argv[1] if len(os.sys.argv) > 1 else "staging")
    repo_root = Path(os.environ.get("SATURN_REPO_ROOT", Path(__file__).resolve().parents[2]))
    data_root = Path(os.environ.get("SATURN_DATA_ROOT", default_data_root(repo_root)))
    image_ref = os.environ.get("SATURN_IMAGE_REF")
    delivery_ref = os.environ.get("SATURN_DELIVERY_REF", "local")

    contract = load_json(data_root / "pipeline_contract.json")
    environment_policy = load_json(data_root / "environment_policy.json")
    rollout_policy = load_json(data_root / "rollout_policy.json")

    if target not in environment_policy:
        raise SystemExit(f"unsupported deployment target: {target}")

    manifest_source = (
        repo_root / rollout_policy["manifest_path"]
        if target == "production"
        else repo_root / "deploy" / "manifests" / "checkout-deployment.yaml"
    )
    manifest = load_yaml(manifest_source)
    rendered_manifest = copy.deepcopy(manifest)
    container = rendered_manifest["spec"]["template"]["spec"]["containers"][0]
    if image_ref:
        container["image"] = image_ref

    artifact_root = repo_root / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    manifest_output = artifact_root / f"{target}-manifest.yaml"
    manifest_output.write_text(yaml.safe_dump(rendered_manifest, sort_keys=False), encoding="utf-8")

    payload = {
        "target": target,
        "environment": {
            "name": environment_policy[target]["environment_name"],
            "review_required": bool(environment_policy[target]["review_required"]),
            "serialized": bool(environment_policy[target]["serialized"]),
            "deployment_window": environment_policy[target]["deployment_window"],
        },
        "delivery": {
            "service": contract["service_name"],
            "ref": delivery_ref,
            "image": container["image"],
        },
        "manifest": {
            "kind": rendered_manifest["kind"],
            "source_path": str(manifest_source.relative_to(repo_root)),
            "rendered_path": str(manifest_output.relative_to(repo_root)),
            "name": rendered_manifest["metadata"]["name"],
            "port": container["ports"][0]["containerPort"],
            "health_path": container["readinessProbe"]["httpGet"]["path"],
        },
    }
    if target == "production":
        canary = rendered_manifest["spec"]["strategy"]["canary"]
        payload["rollout"] = {
            "strategy": contract["rollout_contract"]["strategy"],
            "stable_service": canary["stableService"],
            "canary_service": canary["canaryService"],
            "analysis_templates": [entry["templateName"] for entry in canary.get("analysis", {}).get("templates", [])],
            "steps": canary["steps"],
        }

    summary_output = artifact_root / f"{target}-manifest-summary.json"
    summary_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
