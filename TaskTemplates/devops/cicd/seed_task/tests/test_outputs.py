#!/usr/bin/env python3
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

DATA_ROOT = Path(os.environ.get("SATURN_TEST_DATA_ROOT", "/app/data"))
REPO_ROOT = Path(os.environ.get("SATURN_TEST_REPO_ROOT", "/app/workspace/repo"))
OUTPUT_PATH = REPO_ROOT / "artifacts" / "release_bundle.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts"
INPUT_HASH_PATH = Path(os.environ.get("SATURN_TEST_INPUT_HASH_PATH", "/opt/cicd-input.sha256"))
EXPECTED_STAGE_CHAIN = ["verify", "publish", "staging", "production", "summary"]
EXPECTED_NODE_VERSIONS = ["18.x", "20.x"]
EXPECTED_SUMMARY_ACTIONS = ["actions/checkout@v4", "actions/upload-artifact@v4"]
EXPECTED_RUNTIME_INPUT = "node-version"
EXPECTED_PUBLISH_PERMISSIONS = {"contents": "read", "packages": "write"}
REVIEW_WORKFLOW_PATH = Path(".github/workflows/verify.yml")
RELEASE_WORKFLOW_PATH = Path(".github/workflows/release.yml")
REUSABLE_WORKFLOW_PATH = Path(".github/workflows/reusable-verify.yml")
REVIEW_WORKFLOW_NAME = "Saturn Checkout Verify"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def workflow_on(workflow: dict) -> dict:
    value = workflow.get("on")
    if value is None:
        value = workflow.get(True)
    return value or {}


def compute_hash_listing(root: Path) -> str:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = path.relative_to(root).as_posix()
        lines.append(f"{digest}  {rel}")
    return "\n".join(lines) + "\n"


def run(cmd: str, cwd: Path = REPO_ROOT):
    return subprocess.run(
        ["/bin/bash", "-lc", cmd],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


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


def assert_effective_permissions(workflow: dict, job: dict, expected: dict[str, str]) -> None:
    workflow_permissions = workflow.get("permissions") or {}
    job_permissions = job.get("permissions") or {}
    for key, value in expected.items():
        effective_value = job_permissions.get(key, workflow_permissions.get(key))
        assert effective_value == value, f"expected effective permission {key}={value}"


def resolve_stage_jobs(jobs: dict) -> dict[str, tuple[str, dict]]:
    verify = ("verify", jobs["verify"])
    publish = ("publish", jobs["publish"])
    staging = ("staging", jobs["staging"])
    production = ("production", jobs["production"])
    summary = ("summary", jobs["summary"])
    return {
        "verify": verify,
        "publish": publish,
        "staging": staging,
        "production": production,
        "summary": summary,
    }


def find_step_with_run(job: dict, expected: str) -> dict:
    for step in job.get("steps", []):
        if isinstance(step, dict) and step.get("run") == expected:
            return step
    raise AssertionError(f"missing step: {expected}")


def assert_setup_node_uses_shared_input(reusable: dict) -> None:
    setup_node = None
    for job in reusable["jobs"].values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if step.get("uses") == "actions/setup-node@v4":
                setup_node = step
                break
        if setup_node is not None:
            break
    assert setup_node is not None, "expected reusable workflow to set up node"
    node_version_value = setup_node["with"]["node-version"]
    assert node_version_value in {
        "${{ inputs.node-version }}",
        "${{ inputs['node-version'] }}",
    }
    assert setup_node["with"]["cache"] == "npm"


def assert_publish_push_value(value: object) -> None:
    accepted = {
        True,
        "${{ github.event_name != 'pull_request' }}",
        "${{ github.event_name == 'push' }}",
    }
    assert value in accepted, "expected publish step to push images only on release-path events"


def assert_if_contains_event(value: object, expected_event: str) -> None:
    normalized = str(value).strip()
    accepted = {
        f"github.event_name == '{expected_event}'",
        f"${{{{ github.event_name == '{expected_event}' }}}}",
    }
    assert normalized in accepted, f"expected condition to gate on github.event_name == '{expected_event}'"


def assert_production_if(value: object, publish_event: str, tag_prefix: str) -> None:
    accepted = {
        f"github.event_name == '{publish_event}' && startsWith(github.ref, '{tag_prefix}')",
        f"startsWith(github.ref, '{tag_prefix}')",
        f"${{{{ github.event_name == '{publish_event}' && startsWith(github.ref, '{tag_prefix}') }}}}",
        f"${{{{ startsWith(github.ref, '{tag_prefix}') }}}}",
    }
    assert value in accepted, "expected production stage to remain gated by release tags"


def assert_publish_login_uses_repo_token(job: dict) -> None:
    login_step = next(
        (
            step
            for step in job.get("steps", [])
            if isinstance(step, dict) and str(step.get("uses", "")).startswith("docker/login-action@v")
        ),
        None,
    )
    assert login_step is not None, "expected container registry login step"
    login_with = login_step.get("with", {})
    assert login_with.get("password") == "${{ secrets.GITHUB_TOKEN }}", "expected publish login to use repository token context"


def assert_job_has_serialization(job: dict, stage_name: str) -> None:
    concurrency = job.get("concurrency")
    assert isinstance(concurrency, dict), f"expected {stage_name} stage to declare concurrency controls"
    assert str(concurrency.get("group", "")).strip(), f"expected {stage_name} stage to declare a concurrency group"
    assert concurrency.get("cancel-in-progress") is False, f"expected {stage_name} stage to avoid replacing an in-flight deploy"


def assert_publish_keeps_branch_ref_trace(job: dict) -> None:
    steps = [step for step in job.get("steps", []) if isinstance(step, dict)]
    metadata_step = next(
        (step for step in steps if str(step.get("uses", "")).startswith("docker/metadata-action@v")),
        None,
    )
    if metadata_step is not None:
        metadata_tags = str((metadata_step.get("with") or {}).get("tags", ""))
        if "type=ref,event=branch" in metadata_tags:
            return

    build_step = next(
        (step for step in steps if str(step.get("uses", "")).startswith("docker/build-push-action@v")),
        None,
    )
    assert build_step is not None, "expected publish workflow to build and publish an image"
    build_tags = str((build_step.get("with") or {}).get("tags", ""))
    if "github.ref_name" in build_tags:
        return

    for step in steps:
        if not step.get("id"):
            continue
        run_text = str(step.get("run", ""))
        if "REF_NAME=" in run_text and "GITHUB_REF_NAME" in run_text and f"steps.{step['id']}.outputs" in build_tags:
            return

    raise AssertionError("expected publish workflow to keep a branch-ref image tag path for non-tag delivery refs")


def assert_upload_artifact_paths(job: dict, expected_paths: set[str]) -> None:
    upload_steps = [
        step
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("uses") == "actions/upload-artifact@v4"
    ]
    assert upload_steps, "expected an upload-artifact step"
    actual_paths = set(normalize_path_values(upload_steps[-1].get("with", {}).get("path")))
    assert expected_paths.issubset(actual_paths), f"expected upload paths {expected_paths}, got {actual_paths}"


def assert_immutable_publish_output(job: dict) -> str:
    outputs = job.get("outputs", {})
    build_step = next(
        (
            step
            for step in job.get("steps", [])
            if isinstance(step, dict) and str(step.get("uses", "")).startswith("docker/build-push-action@v")
        ),
        None,
    )
    assert build_step is not None, "expected build-push action"
    build_id = build_step.get("id")
    assert build_id, "expected build-push action to have an id"

    export_step = None
    export_step_id = None
    export_step = next(
        (
            step
            for step in job.get("steps", [])
            if isinstance(step, dict)
            and step.get("id")
            and (
                f"steps.{build_id}.outputs.digest" in str(step.get("run", ""))
                or any(
                    f"steps.{build_id}.outputs.digest" in str(value)
                    for value in (step.get("env") or {}).values()
                )
            )
            and "GITHUB_OUTPUT" in str(step.get("run", ""))
            and "@" in str(step.get("run", ""))
        ),
        None,
    )
    assert export_step is not None, "expected immutable image export step"
    export_step_id = export_step["id"]
    export_run = str(export_step.get("run", ""))
    env_values = [str(value) for value in (export_step.get("env") or {}).values()]
    assert (
        f"steps.{build_id}.outputs.digest" in export_run
        or any(f"steps.{build_id}.outputs.digest" in value for value in env_values)
    ), "expected publish output to use build digest"
    assert "GITHUB_OUTPUT" in export_run and "@" in export_run, "expected digest-based immutable image export"
    for output_name, output_expr in outputs.items():
        match = re.fullmatch(
            rf"\$\{{\{{\s*steps\.{re.escape(export_step_id)}\.outputs\.{re.escape(str(output_name))}\s*\}}\}}",
            str(output_expr),
        )
        if match:
            return str(output_name)
    raise AssertionError("expected publish output to come from the immutable image export step")


def assert_render_uses_publish_output(job: dict, target: str, promoted_output_name: str) -> None:
    render_step = find_step_with_run(job, f"python3 scripts/deploy/render_manifest.py {target}")
    env = render_step.get("env") or {}
    assert env.get("SATURN_IMAGE_REF") == f"${{{{ needs.publish.outputs.{promoted_output_name} }}}}", "expected deploy stage to use the promoted immutable image ref"


def load_case():
    contract = read_json(DATA_ROOT / "pipeline_contract.json")
    env_policy = read_json(DATA_ROOT / "environment_policy.json")
    rollout_policy = read_json(DATA_ROOT / "rollout_policy.json")
    quality_gates = read_json(DATA_ROOT / "quality_gates.json")
    bundle = read_json(OUTPUT_PATH)
    workflow = read_yaml(REPO_ROOT / RELEASE_WORKFLOW_PATH)
    review_workflow = read_yaml(REPO_ROOT / REVIEW_WORKFLOW_PATH)
    reusable = read_yaml(REPO_ROOT / REUSABLE_WORKFLOW_PATH)
    rollout = read_yaml(REPO_ROOT / rollout_policy["manifest_path"])
    deployment = read_yaml(REPO_ROOT / "deploy" / "manifests" / "checkout-deployment.yaml")
    return {
        "contract": contract,
        "env_policy": env_policy,
        "rollout_policy": rollout_policy,
        "quality_gates": quality_gates,
        "bundle": bundle,
        "workflow": workflow,
        "review_workflow": review_workflow,
        "reusable": reusable,
        "rollout": rollout,
        "deployment": deployment,
    }


def test_output_exists_and_input_hash_stable():
    assert OUTPUT_PATH.exists(), "missing release bundle output"
    baseline_hash_listing = INPUT_HASH_PATH.read_text(encoding="utf-8")
    current_hash_listing = compute_hash_listing(DATA_ROOT)
    assert baseline_hash_listing == current_hash_listing, "input data changed"


def test_repo_entrypoints_run():
    run("npm ci")
    run("npm run lint")
    run("npm test")
    run("npm run security-scan")
    run("python3 scripts/deploy/render_manifest.py staging")
    run("python3 scripts/deploy/render_manifest.py production")
    assert (ARTIFACT_ROOT / "staging-manifest-summary.json").exists()
    assert (ARTIFACT_ROOT / "staging-manifest.yaml").exists()
    assert (ARTIFACT_ROOT / "production-manifest-summary.json").exists()
    assert (ARTIFACT_ROOT / "production-manifest.yaml").exists()
    staging_summary = read_json(ARTIFACT_ROOT / "staging-manifest-summary.json")
    production_summary = read_json(ARTIFACT_ROOT / "production-manifest-summary.json")
    assert staging_summary["manifest"]["rendered_path"] == "artifacts/staging-manifest.yaml"
    assert production_summary["manifest"]["rendered_path"] == "artifacts/production-manifest.yaml"


def test_release_workflow_contract():
    case = load_case()
    contract = case["contract"]
    env_policy = case["env_policy"]
    quality_gates = case["quality_gates"]
    workflow = case["workflow"]
    promotion_policy = contract["promotion_policy"]

    assert workflow["name"] == contract["workflow_name"]
    on_clause = workflow_on(workflow)
    assert on_clause["push"]["branches"] == [contract["delivery_refs"]["default_branch"]]
    assert on_clause["push"]["tags"] == [contract["delivery_refs"]["release_tag_glob"]]
    assert "pull_request" not in on_clause
    assert "workflow_dispatch" not in on_clause
    release_serialization = contract["release_serialization"]
    assert workflow["concurrency"]["group"] == release_serialization["group"]
    assert workflow["concurrency"]["cancel-in-progress"] is release_serialization["cancel_in_progress"]

    jobs = workflow["jobs"]
    stage_jobs = resolve_stage_jobs(jobs)
    assert_effective_permissions(workflow, stage_jobs["publish"][1], EXPECTED_PUBLISH_PERMISSIONS)

    verify = stage_jobs["verify"][1]
    assert verify["uses"] == "./.github/workflows/reusable-verify.yml"
    assert verify["strategy"]["matrix"]["node-version"] == contract["verification_policy"]["node_versions"]
    assert verify["with"]["node-version"] in {
        "${{ matrix.node-version }}",
        "${{ matrix['node-version'] }}",
    }

    publish = stage_jobs["publish"][1]
    publish_uses = [step.get("uses") for step in publish["steps"] if "uses" in step]
    assert any(action.startswith("docker/build-push-action@v") for action in publish_uses if action)
    assert_if_contains_event(publish["if"], promotion_policy["publish_event"])
    assert normalize_needs(publish["needs"]) == [stage_jobs["verify"][0]]
    build_step = next(step for step in publish["steps"] if step.get("uses", "").startswith("docker/build-push-action@v"))
    assert_publish_push_value(build_step["with"]["push"])
    assert_publish_login_uses_repo_token(publish)
    assert_publish_keeps_branch_ref_trace(publish)
    promoted_output_name = assert_immutable_publish_output(publish)

    deploy_staging = stage_jobs["staging"][1]
    staging_runs = [step.get("run") for step in deploy_staging["steps"] if "run" in step]
    for required in quality_gates["staging_commands"].values():
        assert required in staging_runs
    assert normalize_needs(deploy_staging["needs"]) == [stage_jobs["publish"][0]]
    assert environment_name(deploy_staging["environment"]) == env_policy["staging"]["environment_name"]
    assert_if_contains_event(deploy_staging["if"], promotion_policy["staging_event"])
    assert_job_has_serialization(deploy_staging, "staging")
    assert_render_uses_publish_output(
        deploy_staging,
        "staging",
        promoted_output_name,
    )
    assert_upload_artifact_paths(
        deploy_staging,
        {
            contract["environment_contract"]["artifact_names"]["staging_summary"],
            contract["environment_contract"]["artifact_names"]["staging_manifest"],
        },
    )

    deploy_production = stage_jobs["production"][1]
    production_runs = [step.get("run") for step in deploy_production["steps"] if "run" in step]
    for required in quality_gates["production_commands"].values():
        assert required in production_runs
    assert stage_jobs["staging"][0] in normalize_needs(deploy_production["needs"])
    assert environment_name(deploy_production["environment"]) == env_policy["production"]["environment_name"]
    assert_production_if(
        deploy_production["if"],
        promotion_policy["publish_event"],
        promotion_policy["production_tag_prefix"],
    )
    assert_job_has_serialization(deploy_production, "production")
    assert_render_uses_publish_output(
        deploy_production,
        "production",
        promoted_output_name,
    )
    assert_upload_artifact_paths(
        deploy_production,
        {
            contract["environment_contract"]["artifact_names"]["production_summary"],
            contract["environment_contract"]["artifact_names"]["production_manifest"],
        },
    )

    release_summary = stage_jobs["summary"][1]
    summary_uses = [step.get("uses") for step in release_summary["steps"] if "uses" in step]
    for required in EXPECTED_SUMMARY_ACTIONS:
        assert required in summary_uses
    summary_runs = [step.get("run") for step in release_summary["steps"] if "run" in step]
    assert {"python3 scripts/release/build_release_bundle.py", "make release-bundle"} & set(summary_runs)
    assert "production" in normalize_needs(release_summary["needs"])
    summary_if = str(release_summary.get("if", "")).strip()
    if summary_if:
        assert f"startsWith(github.ref, '{promotion_policy['summary_tag_prefix']}')" in summary_if


def test_review_workflow_contract():
    case = load_case()
    contract = case["contract"]
    review_workflow = case["review_workflow"]
    review_on = workflow_on(review_workflow)

    assert review_workflow["name"] == REVIEW_WORKFLOW_NAME
    assert "push" in review_on
    assert "pull_request" in review_on
    assert list(review_workflow["jobs"].keys()) == ["verify"]

    verify = review_workflow["jobs"]["verify"]
    assert verify["strategy"]["matrix"]["node-version"] == contract["verification_policy"]["node_versions"]
    assert verify["uses"] == "./.github/workflows/reusable-verify.yml"
    assert verify["with"]["node-version"] in {
        "${{ matrix.node-version }}",
        "${{ matrix['node-version'] }}",
    }


def test_reusable_workflow_contract():
    case = load_case()
    reusable = case["reusable"]
    quality_gates = case["quality_gates"]
    reusable_on = workflow_on(reusable)

    assert "workflow_call" in reusable_on
    assert reusable_on["workflow_call"]["inputs"][EXPECTED_RUNTIME_INPUT]["required"] is True
    assert "workflow_dispatch" in reusable_on
    dispatch_inputs = reusable_on["workflow_dispatch"].get("inputs", {})
    assert EXPECTED_RUNTIME_INPUT in dispatch_inputs
    assert_setup_node_uses_shared_input(reusable)
    verify_steps = [
        step
        for job in reusable["jobs"].values()
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict)
    ]
    verify_runs = [step.get("run") for step in verify_steps if "run" in step]
    assert "npm ci" in verify_runs
    for required in quality_gates["verify_commands"].values():
        assert required in verify_runs


def test_rollout_contract():
    case = load_case()
    rollout_policy = case["rollout_policy"]
    rollout = case["rollout"]
    deployment = case["deployment"]
    contract = case["contract"]

    assert rollout["kind"] == rollout_policy["kind"]
    canary = rollout["spec"]["strategy"]["canary"]
    assert canary["stableService"] == rollout_policy["stable_service"]
    assert canary["canaryService"] == rollout_policy["canary_service"]
    assert [entry["templateName"] for entry in canary["analysis"]["templates"]] == rollout_policy["analysis_templates"]
    steps = canary["steps"]
    assert [step["setWeight"] for step in steps if "setWeight" in step] == [10, 25, 50, 100]
    assert [step["pause"]["duration"] for step in steps if "pause" in step] == ["5m", "5m", "10m"]

    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert deployment["metadata"]["name"] == contract["service_name"]
    assert container["image"] == f"{contract['image_repository']}:latest"
    assert container["ports"][0]["containerPort"] == contract["service_port"]
    assert container["readinessProbe"]["httpGet"]["path"] == contract["health_path"]


def test_environment_manifest_contract():
    case = load_case()
    contract = case["contract"]
    env_policy = case["env_policy"]
    env_contract = contract["environment_contract"]
    staging_summary = read_json(REPO_ROOT / env_contract["artifact_names"]["staging_summary"])
    production_summary = read_json(REPO_ROOT / env_contract["artifact_names"]["production_summary"])
    staging_rendered = read_yaml(REPO_ROOT / env_contract["artifact_names"]["staging_manifest"])
    production_rendered = read_yaml(REPO_ROOT / env_contract["artifact_names"]["production_manifest"])

    assert staging_summary["target"] == "staging"
    assert production_summary["target"] == "production"
    assert staging_summary["environment"]["name"] == env_policy["staging"]["environment_name"]
    assert production_summary["environment"]["name"] == env_policy["production"]["environment_name"]
    assert staging_summary["manifest"]["source_path"] == env_contract["manifest_sources"]["staging"]
    assert production_summary["manifest"]["source_path"] == env_contract["manifest_sources"]["production"]
    assert staging_summary["manifest"]["rendered_path"] == env_contract["artifact_names"]["staging_manifest"]
    assert production_summary["manifest"]["rendered_path"] == env_contract["artifact_names"]["production_manifest"]
    assert staging_summary["environment"]["review_required"] is False
    assert production_summary["environment"]["review_required"] is True
    assert staging_summary["environment"]["serialized"] is True
    assert production_summary["environment"]["serialized"] is True
    assert staging_summary["environment"]["deployment_window"] == env_policy["staging"]["deployment_window"]
    assert production_summary["environment"]["deployment_window"] == env_policy["production"]["deployment_window"]
    assert staging_summary["manifest"]["kind"] == "Deployment"
    assert production_summary["manifest"]["kind"] == env_contract["production_manifest_kind"]
    assert staging_rendered["kind"] == "Deployment"
    assert production_rendered["kind"] == env_contract["production_manifest_kind"]
    assert staging_rendered["spec"]["template"]["spec"]["containers"][0]["ports"][0]["containerPort"] == contract["service_port"]
    assert production_rendered["spec"]["template"]["spec"]["containers"][0]["ports"][0]["containerPort"] == contract["service_port"]


def test_release_bundle_contract():
    case = load_case()
    contract = case["contract"]
    rollout_policy = case["rollout_policy"]
    bundle = case["bundle"]

    required_keys = {
        "service",
        "workflow_name",
        "workflow_path",
        "review_workflow_path",
        "reusable_verify_workflow",
        "verification",
        "delivery_refs",
        "quality_gates",
        "environments",
        "stage_chain",
        "production_rollout",
        "status",
    }
    assert required_keys.issubset(bundle.keys())
    assert bundle["service"] == contract["service_name"]
    assert bundle["workflow_name"] == contract["workflow_name"]
    assert bundle["workflow_path"] == RELEASE_WORKFLOW_PATH.as_posix()
    assert bundle["review_workflow_path"] == REVIEW_WORKFLOW_PATH.as_posix()
    assert bundle["reusable_verify_workflow"] == REUSABLE_WORKFLOW_PATH.as_posix()
    assert bundle["verification"]["runtime_input"] == EXPECTED_RUNTIME_INPUT
    assert bundle["verification"]["node_versions"] == EXPECTED_NODE_VERSIONS
    assert bundle["delivery_refs"] == contract["delivery_refs"]
    assert bundle["quality_gates"] == ["lint", "unit", "security_scan", "smoke", "e2e"]
    assert bundle["environments"]["staging"] == case["env_policy"]["staging"]["environment_name"]
    assert bundle["environments"]["production"] == case["env_policy"]["production"]["environment_name"]
    assert bundle["stage_chain"] == EXPECTED_STAGE_CHAIN
    assert bundle["production_rollout"]["weights"] == [10, 25, 50, 100]
    assert bundle["production_rollout"]["pauses"] == ["5m", "5m", "10m"]
    assert bundle["production_rollout"]["analysis_templates"] == rollout_policy["analysis_templates"]
    assert bundle["status"] == "ready"


def test_bundle_rerun_is_stable():
    before = read_json(OUTPUT_PATH)
    OUTPUT_PATH.unlink()
    rerun = run("python3 scripts/release/build_release_bundle.py")
    assert OUTPUT_PATH.exists(), "bundle entrypoint failed to recreate the output"
    after = read_json(OUTPUT_PATH)
    assert after == before, "bundle entrypoint is not stable across reruns"
    assert "ready" in rerun.stdout


def test_rollout_mutation_is_rejected():
    with tempfile.TemporaryDirectory(prefix="saturn-mutate-") as temp_dir:
        temp_root = Path(temp_dir) / "repo"
        shutil.copytree(REPO_ROOT, temp_root)
        rollout_path = temp_root / "deploy" / "rollouts" / "checkout-production-rollout.yaml"
        mutated = rollout_path.read_text(encoding="utf-8").replace("setWeight: 50", "setWeight: 40", 1)
        rollout_path.write_text(mutated, encoding="utf-8")
        mutated_output = temp_root / "artifacts" / "mutated_bundle.json"
        result = subprocess.run(
            ["/bin/bash", "-lc", "python3 scripts/release/build_release_bundle.py"],
            cwd=temp_root,
            text=True,
            capture_output=True,
            env={
                "SATURN_REPO_ROOT": str(temp_root),
                "SATURN_DATA_ROOT": str(DATA_ROOT),
                "SATURN_OUTPUT_PATH": str(mutated_output),
                "PATH": "/usr/local/bin:/usr/bin:/bin",
            },
        )
        assert result.returncode != 0, "bundle entrypoint ignored rollout mutation"
        assert "release rollout contract drift detected" in (result.stderr + result.stdout)


def test_reusable_workflow_mutation_is_rejected():
    with tempfile.TemporaryDirectory(prefix="saturn-mutate-") as temp_dir:
        temp_root = Path(temp_dir) / "repo"
        shutil.copytree(REPO_ROOT, temp_root)
        reusable_path = temp_root / ".github" / "workflows" / "reusable-verify.yml"
        mutated = reusable_path.read_text(encoding="utf-8").replace("node-version:", "runtime-version:", 1)
        reusable_path.write_text(mutated, encoding="utf-8")
        mutated_output = temp_root / "artifacts" / "mutated_bundle.json"
        result = subprocess.run(
            ["/bin/bash", "-lc", "python3 scripts/release/build_release_bundle.py"],
            cwd=temp_root,
            text=True,
            capture_output=True,
            env={
                "SATURN_REPO_ROOT": str(temp_root),
                "SATURN_DATA_ROOT": str(DATA_ROOT),
                "SATURN_OUTPUT_PATH": str(mutated_output),
                "PATH": "/usr/local/bin:/usr/bin:/bin",
            },
        )
        assert result.returncode != 0, "bundle entrypoint ignored reusable workflow mutation"
        assert (
            "release workflow contract drift detected" in (result.stderr + result.stdout)
            or "release workflow summary drift detected" in (result.stderr + result.stdout)
        )
