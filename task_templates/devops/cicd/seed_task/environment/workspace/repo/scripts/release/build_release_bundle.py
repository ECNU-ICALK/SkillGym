#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

import yaml


RELEASE_WORKFLOW_PATH = Path(".github/workflows/release.yml")
REVIEW_WORKFLOW_PATH = Path(".github/workflows/verify.yml")
REUSABLE_WORKFLOW_PATH = Path(".github/workflows/reusable-verify.yml")
OUTPUT_EXPR = re.compile(r"\$\{\{\s*steps\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)\s*\}\}")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def default_data_root(repo_root: Path) -> Path:
    sibling = repo_root.parents[1] / "data"
    if sibling.exists():
        return sibling
    return Path("/app/data")


def workflow_on(workflow: dict) -> dict:
    value = workflow.get("on")
    if value is None:
        value = workflow.get(True)
    return value or {}


def normalize_needs(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def normalize_path_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def environment_name(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("name")
    return None


def rollout_steps(steps: list[dict]) -> tuple[list[int], list[str]]:
    weights = []
    pauses = []
    for step in steps:
        if "setWeight" in step:
            weights.append(int(step["setWeight"]))
        pause = step.get("pause")
        if isinstance(pause, dict) and "duration" in pause:
            pauses.append(str(pause["duration"]))
    return weights, pauses


def step_uses(steps: list[dict], prefix: str) -> dict:
    for step in steps:
        if isinstance(step, dict) and str(step.get("uses", "")).startswith(prefix):
            return step
    raise AssertionError("release workflow contract drift detected")


def upload_step_paths(job: dict) -> list[str]:
    for step in job.get("steps", []):
        if isinstance(step, dict) and step.get("uses") == "actions/upload-artifact@v4":
            return normalize_path_values(step.get("with", {}).get("path"))
    raise AssertionError("release workflow contract drift detected")


def find_render_step(job: dict, target: str) -> dict:
    expected = f"python3 scripts/deploy/render_manifest.py {target}"
    for step in job.get("steps", []):
        if isinstance(step, dict) and step.get("run") == expected:
            return step
    raise AssertionError("release workflow contract drift detected")


def resolve_runtime_value(value: object) -> str:
    runtime_value = str(value)
    accepted = {"${{ matrix.node-version }}", "${{ matrix['node-version'] }}"}
    if runtime_value not in accepted:
        raise AssertionError("release workflow contract drift detected")
    return runtime_value


def find_publish_output_name(publish: dict) -> str:
    steps = publish.get("steps", [])
    build_step = step_uses(steps, "docker/build-push-action@v")
    build_id = str(build_step.get("id") or "").strip()
    if not build_id:
        raise AssertionError("release workflow contract drift detected")

    digest_reference = f"steps.{build_id}.outputs.digest"
    export_step_id = None
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "").strip()
        run_text = str(step.get("run", ""))
        env_values = [str(value) for value in (step.get("env") or {}).values()]
        if not step_id:
            continue
        if "GITHUB_OUTPUT" not in run_text or "@" not in run_text:
            continue
        if digest_reference in run_text or any(digest_reference in value for value in env_values):
            export_step_id = step_id
            break

    if export_step_id is None:
        raise AssertionError("release workflow contract drift detected")

    for output_name, output_value in (publish.get("outputs") or {}).items():
        match = OUTPUT_EXPR.fullmatch(str(output_value))
        if not match:
            continue
        step_id, step_output = match.groups()
        if step_id == export_step_id and step_output == output_name:
            return output_name

    raise AssertionError("release workflow contract drift detected")


def require_release_workflow(workflow: dict, contract: dict, quality_gates: dict) -> str:
    workflow_on_config = workflow_on(workflow)
    if workflow.get("name") != contract["workflow_name"]:
        raise AssertionError("release workflow contract drift detected")
    if workflow_on_config.get("push", {}).get("branches") != [contract["delivery_refs"]["default_branch"]]:
        raise AssertionError("release workflow contract drift detected")
    if workflow_on_config.get("push", {}).get("tags") != [contract["delivery_refs"]["release_tag_glob"]]:
        raise AssertionError("release workflow contract drift detected")
    if "pull_request" in workflow_on_config or "workflow_dispatch" in workflow_on_config:
        raise AssertionError("release workflow contract drift detected")

    concurrency = workflow.get("concurrency", {})
    if concurrency.get("group") != contract["release_serialization"]["group"]:
        raise AssertionError("release workflow contract drift detected")
    if concurrency.get("cancel-in-progress") != contract["release_serialization"]["cancel_in_progress"]:
        raise AssertionError("release workflow contract drift detected")

    jobs = workflow.get("jobs", {})
    if list(jobs.keys()) != contract["delivery_stages"]:
        raise AssertionError("release workflow contract drift detected")

    runtime_input = contract["verification_policy"]["runtime_input_name"]
    verify = jobs["verify"]
    if verify.get("uses") != f"./{REUSABLE_WORKFLOW_PATH.as_posix()}":
        raise AssertionError("release workflow contract drift detected")
    if verify.get("strategy", {}).get("matrix", {}).get(runtime_input) != contract["verification_policy"]["node_versions"]:
        raise AssertionError("release workflow contract drift detected")
    resolve_runtime_value(verify.get("with", {}).get(runtime_input))

    publish = jobs["publish"]
    if normalize_needs(publish.get("needs")) != ["verify"]:
        raise AssertionError("release workflow contract drift detected")
    if contract["promotion_policy"]["publish_event"] not in str(publish.get("if", "")):
        raise AssertionError("release workflow contract drift detected")
    promoted_output_name = find_publish_output_name(publish)

    staging = jobs["staging"]
    if normalize_needs(staging.get("needs")) != ["publish"]:
        raise AssertionError("release workflow contract drift detected")
    if contract["promotion_policy"]["staging_event"] not in str(staging.get("if", "")):
        raise AssertionError("release workflow contract drift detected")
    if environment_name(staging.get("environment")) != contract["environment_contract"]["staging_name"]:
        raise AssertionError("release workflow contract drift detected")
    staging_runs = [step.get("run") for step in staging.get("steps", []) if isinstance(step, dict) and "run" in step]
    for required in quality_gates["staging_commands"].values():
        if required not in staging_runs:
            raise AssertionError("release workflow contract drift detected")
    staging_render = find_render_step(staging, "staging")
    staging_image_ref = str((staging_render.get("env") or {}).get("SATURN_IMAGE_REF", ""))
    if staging_image_ref != f"${{{{ needs.publish.outputs.{promoted_output_name} }}}}":
        raise AssertionError("release workflow contract drift detected")
    required_staging_paths = {
        contract["environment_contract"]["artifact_names"]["staging_summary"],
        contract["environment_contract"]["artifact_names"]["staging_manifest"],
    }
    if not required_staging_paths.issubset(set(upload_step_paths(staging))):
        raise AssertionError("release workflow contract drift detected")

    production = jobs["production"]
    if "staging" not in normalize_needs(production.get("needs")):
        raise AssertionError("release workflow contract drift detected")
    production_if = str(production.get("if", ""))
    if contract["promotion_policy"]["production_tag_prefix"] not in production_if:
        raise AssertionError("release workflow contract drift detected")
    if environment_name(production.get("environment")) != contract["environment_contract"]["production_name"]:
        raise AssertionError("release workflow contract drift detected")
    production_runs = [step.get("run") for step in production.get("steps", []) if isinstance(step, dict) and "run" in step]
    for required in quality_gates["production_commands"].values():
        if required not in production_runs:
            raise AssertionError("release workflow contract drift detected")
    production_render = find_render_step(production, "production")
    production_image_ref = str((production_render.get("env") or {}).get("SATURN_IMAGE_REF", ""))
    if production_image_ref != f"${{{{ needs.publish.outputs.{promoted_output_name} }}}}":
        raise AssertionError("release workflow contract drift detected")
    required_production_paths = {
        contract["environment_contract"]["artifact_names"]["production_summary"],
        contract["environment_contract"]["artifact_names"]["production_manifest"],
    }
    if not required_production_paths.issubset(set(upload_step_paths(production))):
        raise AssertionError("release workflow contract drift detected")

    summary = jobs["summary"]
    if "production" not in normalize_needs(summary.get("needs")):
        raise AssertionError("release workflow contract drift detected")
    summary_runs = [step.get("run") for step in summary.get("steps", []) if isinstance(step, dict) and "run" in step]
    if "make release-bundle" not in summary_runs and "python3 scripts/release/build_release_bundle.py" not in summary_runs:
        raise AssertionError("release workflow contract drift detected")

    return promoted_output_name


def require_review_workflow(review_workflow: dict, contract: dict) -> None:
    review_on = workflow_on(review_workflow)
    runtime_input = contract["verification_policy"]["runtime_input_name"]
    if "push" not in review_on or "pull_request" not in review_on:
        raise AssertionError("release workflow contract drift detected")
    if list(review_workflow.get("jobs", {}).keys()) != ["verify"]:
        raise AssertionError("release workflow contract drift detected")

    verify = review_workflow["jobs"]["verify"]
    if verify.get("uses") != f"./{REUSABLE_WORKFLOW_PATH.as_posix()}":
        raise AssertionError("release workflow contract drift detected")
    if verify.get("strategy", {}).get("matrix", {}).get(runtime_input) != contract["verification_policy"]["node_versions"]:
        raise AssertionError("release workflow contract drift detected")
    resolve_runtime_value(verify.get("with", {}).get(runtime_input))


def require_reusable_workflow(reusable: dict, contract: dict, quality_gates: dict) -> None:
    reusable_on = workflow_on(reusable)
    runtime_input = contract["verification_policy"]["runtime_input_name"]
    workflow_call = reusable_on.get("workflow_call", {})
    runtime = (workflow_call.get("inputs") or {}).get(runtime_input, {})
    if runtime.get("required") is not True or runtime.get("type") != "string":
        raise AssertionError("release workflow contract drift detected")

    dispatch_inputs = (reusable_on.get("workflow_dispatch") or {}).get("inputs", {})
    if runtime_input not in dispatch_inputs:
        raise AssertionError("release workflow contract drift detected")

    jobs = reusable.get("jobs", {})
    if len(jobs) != 1:
        raise AssertionError("release workflow contract drift detected")

    verify_job = next(iter(jobs.values()))
    setup_node_found = False
    verify_runs = []
    for step in verify_job.get("steps", []):
        if not isinstance(step, dict):
            continue
        if step.get("uses") == "actions/setup-node@v4":
            node_value = str(step.get("with", {}).get("node-version", ""))
            if node_value not in {"${{ inputs.node-version }}", "${{ inputs['node-version'] }}"}:
                raise AssertionError("release workflow contract drift detected")
            setup_node_found = True
        if "run" in step:
            verify_runs.append(step["run"])

    if not setup_node_found:
        raise AssertionError("release workflow contract drift detected")
    if "npm ci" not in verify_runs:
        raise AssertionError("release workflow contract drift detected")
    for required_command in quality_gates["verify_commands"].values():
        if required_command not in verify_runs:
            raise AssertionError("release workflow contract drift detected")


def require_rollout_contract(rollout: dict, rollout_policy: dict) -> tuple[list[int], list[str], list[str]]:
    if rollout.get("kind") != rollout_policy["kind"]:
        raise AssertionError("release rollout contract drift detected")
    if rollout.get("metadata", {}).get("name") != rollout_policy["service_name"]:
        raise AssertionError("release rollout contract drift detected")

    canary = rollout.get("spec", {}).get("strategy", {}).get("canary", {})
    if canary.get("stableService") != rollout_policy["stable_service"]:
        raise AssertionError("release rollout contract drift detected")
    if canary.get("canaryService") != rollout_policy["canary_service"]:
        raise AssertionError("release rollout contract drift detected")

    analysis_templates = [
        entry.get("templateName")
        for entry in canary.get("analysis", {}).get("templates", [])
        if isinstance(entry, dict)
    ]
    if analysis_templates != rollout_policy["analysis_templates"]:
        raise AssertionError("release rollout contract drift detected")

    expected_weights = [item["setWeight"] for item in rollout_policy["steps"] if "setWeight" in item]
    expected_pauses = [item["pause"] for item in rollout_policy["steps"] if "pause" in item]
    actual_weights, actual_pauses = rollout_steps(canary.get("steps", []))
    if actual_weights != expected_weights or actual_pauses != expected_pauses:
        raise AssertionError("release rollout contract drift detected")

    return actual_weights, actual_pauses, analysis_templates


def main() -> None:
    repo_root = Path(os.environ.get("SATURN_REPO_ROOT", Path(__file__).resolve().parents[2]))
    data_root = Path(os.environ.get("SATURN_DATA_ROOT", default_data_root(repo_root)))
    output_path = Path(os.environ.get("SATURN_OUTPUT_PATH", repo_root / "artifacts" / "release_bundle.json"))

    contract = read_json(data_root / "pipeline_contract.json")
    env_policy = read_json(data_root / "environment_policy.json")
    rollout_policy = read_json(data_root / "rollout_policy.json")
    quality_gates = read_json(data_root / "quality_gates.json")

    workflow = read_yaml(repo_root / RELEASE_WORKFLOW_PATH)
    review_workflow = read_yaml(repo_root / REVIEW_WORKFLOW_PATH)
    reusable = read_yaml(repo_root / REUSABLE_WORKFLOW_PATH)
    rollout = read_yaml(repo_root / rollout_policy["manifest_path"])

    if "jobs" not in workflow or not isinstance(workflow["jobs"], dict):
        raise AssertionError("release workflow contract drift detected")
    if "jobs" not in review_workflow or not isinstance(review_workflow["jobs"], dict):
        raise AssertionError("release workflow contract drift detected")
    if "jobs" not in reusable or not isinstance(reusable["jobs"], dict):
        raise AssertionError("release workflow contract drift detected")

    require_release_workflow(workflow, contract, quality_gates)
    require_review_workflow(review_workflow, contract)
    require_reusable_workflow(reusable, contract, quality_gates)
    weights, pauses, analysis_templates = require_rollout_contract(rollout, rollout_policy)

    bundle = {
        "service": contract["service_name"],
        "workflow_name": workflow["name"],
        "workflow_path": RELEASE_WORKFLOW_PATH.as_posix(),
        "review_workflow_path": REVIEW_WORKFLOW_PATH.as_posix(),
        "reusable_verify_workflow": REUSABLE_WORKFLOW_PATH.as_posix(),
        "verification": {
            "runtime_input": contract["verification_policy"]["runtime_input_name"],
            "node_versions": contract["verification_policy"]["node_versions"],
        },
        "delivery_refs": contract["delivery_refs"],
        "quality_gates": list(quality_gates["verify_commands"].keys()) + list(quality_gates["staging_commands"].keys())[1:],
        "environments": {
            "staging": env_policy["staging"]["environment_name"],
            "production": env_policy["production"]["environment_name"],
        },
        "stage_chain": list(workflow["jobs"].keys()),
        "production_rollout": {
            "strategy": contract["rollout_contract"]["strategy"],
            "weights": weights,
            "pauses": pauses,
            "analysis_templates": analysis_templates,
        },
        "status": "ready",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
