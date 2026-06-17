from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml


APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
WORKSPACE = APP_ROOT / "workspace"
CHART_DIR = WORKSPACE / "chart"
RELEASES_DIR = WORKSPACE / "releases"
SCRIPTS_DIR = WORKSPACE / "scripts"
DATA_DIR = APP_ROOT / "data"

APP_CONTRACT = json.loads((DATA_DIR / "app_contract.json").read_text(encoding="utf-8"))
RELEASE_MATRIX = yaml.safe_load((DATA_DIR / "release_matrix.yaml").read_text(encoding="utf-8"))
PLATFORM_LABELS = json.loads((DATA_DIR / "platform_labels.json").read_text(encoding="utf-8"))
RENDER_CONTRACT = json.loads((DATA_DIR / "render_contract.json").read_text(encoding="utf-8"))


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=check,
    )


def render_release(release_key: str, release_name: str | None = None, namespace: str | None = None) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp:
        cmd = ["bash", str(SCRIPTS_DIR / "render_release.sh"), release_key, tmp.name]
        if release_name is not None:
            cmd.append(release_name)
        if namespace is not None:
            if release_name is None:
                cmd.append(release_key)
            cmd.append(namespace)
        result = run(cmd)
        assert result.returncode == 0, result.stderr
        docs = [doc for doc in yaml.safe_load_all(Path(tmp.name).read_text(encoding="utf-8")) if doc]
        assert docs, f"render_release.sh produced no documents for {release_key}"
        return docs


def render_hidden(values: dict, release_name: str = "qa-canary") -> list[dict]:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8") as values_file, tempfile.NamedTemporaryFile(
        suffix=".yaml"
    ) as output_file:
        yaml.safe_dump(values, values_file, sort_keys=False)
        values_file.flush()
        result = run(
            [
                "helm",
                "template",
                release_name,
                str(CHART_DIR),
                "--namespace",
                values["namespace"],
                "-f",
                str(CHART_DIR / "values.yaml"),
                "-f",
                values_file.name,
            ]
        )
        Path(output_file.name).write_text(result.stdout, encoding="utf-8")
        return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def lint_release(release_key: str) -> None:
    result = run(
        [
            "helm",
            "lint",
            str(CHART_DIR),
            "-f",
            str(CHART_DIR / "values.yaml"),
            "-f",
            str(RELEASES_DIR / f"{release_key}.yaml"),
        ]
    )
    assert "0 chart(s) failed" in result.stdout, result.stdout + result.stderr


def docs_by_kind(docs: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for doc in docs:
        annotations = doc.get("metadata", {}).get("annotations", {})
        if annotations.get("helm.sh/hook") == "test":
            continue
        grouped.setdefault(doc["kind"], []).append(doc)
    return grouped


def one(docs: list[dict], kind: str) -> dict:
    matches = [doc for doc in docs if doc["kind"] == kind]
    assert len(matches) == 1, f"Expected exactly one {kind}, found {len(matches)}"
    return matches[0]


def expected_config_for(release_key: str) -> dict[str, str]:
    app_config = dict(APP_CONTRACT["application"]["config"])
    app_config.update(RELEASE_MATRIX["releases"][release_key]["config"])
    return app_config


def assert_labels(labels: dict, environment: str, release_name: str) -> None:
    required = PLATFORM_LABELS["required_labels"]
    for key, value in required.items():
        assert labels.get(key) == value
    assert labels.get("app.kubernetes.io/name") == APP_CONTRACT["application"]["name"]
    assert labels.get("app.kubernetes.io/instance") == release_name
    assert labels.get("platform.example.com/environment") == environment


def assert_selector_contract(deployment: dict, service: dict, release_name: str) -> None:
    match_labels = deployment["spec"]["selector"]["matchLabels"]
    pod_labels = deployment["spec"]["template"]["metadata"]["labels"]
    service_selector = service["spec"]["selector"]

    assert match_labels == service_selector
    assert match_labels["app.kubernetes.io/name"] == APP_CONTRACT["application"]["name"]
    assert match_labels["app.kubernetes.io/instance"] == release_name
    for key, value in match_labels.items():
        assert pod_labels.get(key) == value


def assert_common_resource_contract(docs: list[dict], release_key: str, release_name: str) -> None:
    expected = RELEASE_MATRIX["releases"][release_key]
    expected_render = RENDER_CONTRACT["releases"][release_key]
    grouped = docs_by_kind(docs)

    assert sorted(grouped) == sorted(expected_render["must_render"]), sorted(grouped)

    config_map = one(docs, "ConfigMap")
    deployment = one(docs, "Deployment")
    service = one(docs, "Service")
    pdb = one(docs, "PodDisruptionBudget")
    service_account = one(docs, "ServiceAccount")

    assert config_map["metadata"]["namespace"] == expected["namespace"]
    assert deployment["metadata"]["namespace"] == expected["namespace"]
    assert service["metadata"]["namespace"] == expected["namespace"]
    assert pdb["metadata"]["namespace"] == expected["namespace"]
    assert service_account["metadata"]["namespace"] == expected["namespace"]

    for doc in (config_map, deployment, service, pdb, service_account):
        assert_labels(doc["metadata"]["labels"], expected["environment"], release_name)

    assert_labels(deployment["spec"]["template"]["metadata"]["labels"], expected["environment"], release_name)
    assert_selector_contract(deployment, service, release_name)

    assert config_map["data"] == expected_config_for(release_key)
    annotations = deployment["spec"]["template"]["metadata"]["annotations"]
    assert "checksum/config" in annotations
    assert len(annotations["checksum/config"]) >= 32

    container = deployment["spec"]["template"]["spec"]["containers"][0]
    image = APP_CONTRACT["application"]["image"]
    assert container["image"] == f"{image['repository']}:{image['tag']}"
    assert container["imagePullPolicy"] == image["pullPolicy"]
    assert container["readinessProbe"]["httpGet"] == {"path": "/readyz", "port": "http"}
    assert container["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert container["resources"] == APP_CONTRACT["application"]["resources"]
    assert container["envFrom"] == [{"configMapRef": {"name": config_map["metadata"]["name"]}}]

    secret_env = expected["secretEnv"][0]
    assert container["env"][0] == {
        "name": secret_env["name"],
        "valueFrom": {
            "secretKeyRef": {
                "name": secret_env["secretName"],
                "key": secret_env["key"],
            }
        },
    }

    ports = {port["name"]: port for port in container["ports"]}
    assert ports["http"]["containerPort"] == APP_CONTRACT["application"]["container"]["port"]
    assert ports["metrics"]["containerPort"] == APP_CONTRACT["application"]["service"]["metricsPort"]

    service_ports = {port["name"]: port for port in service["spec"]["ports"]}
    assert service_ports["http"]["port"] == APP_CONTRACT["application"]["service"]["port"]
    assert service_ports["http"]["targetPort"] == "http"
    assert service_ports["metrics"]["port"] == APP_CONTRACT["application"]["service"]["metricsPort"]
    assert service_ports["metrics"]["targetPort"] == "metrics"

    assert deployment["spec"]["template"]["spec"]["serviceAccountName"] == service_account["metadata"]["name"]
    assert pdb["spec"]["minAvailable"] == expected_render["pdb_min_available"]


class TestChartStructure:
    def test_required_chart_files_exist(self) -> None:
        for relative in RENDER_CONTRACT["required_chart_files"]:
            assert (CHART_DIR / relative).exists(), f"Missing chart file: {relative}"

    def test_chart_support_files_are_wired(self) -> None:
        helmignore = (CHART_DIR / ".helmignore").read_text(encoding="utf-8")
        notes = (CHART_DIR / "templates" / "NOTES.txt").read_text(encoding="utf-8")
        test_connection = (CHART_DIR / "templates" / "tests" / "test-connection.yaml").read_text(encoding="utf-8")

        assert len([line for line in helmignore.splitlines() if line.strip()]) >= 3
        assert "{{" in notes
        assert '"helm.sh/hook": test' in test_connection or "helm.sh/hook: test" in test_connection
        assert "{{" in test_connection

    @pytest.mark.parametrize("release_key", ["staging", "prod"])
    def test_helm_lint_passes_for_visible_releases(self, release_key: str) -> None:
        lint_release(release_key)


class TestVisibleReleaseBehavior:
    def test_staging_render_contract(self) -> None:
        docs = render_release("staging", "staging")
        assert_common_resource_contract(docs, "staging", "staging")

        grouped = docs_by_kind(docs)
        assert "HorizontalPodAutoscaler" not in grouped

        ingress = one(docs, "Ingress")
        assert ingress["spec"]["ingressClassName"] == "nginx"
        assert ingress["spec"]["rules"][0]["host"] == RENDER_CONTRACT["releases"]["staging"]["ingress_host"]
        backend_port = ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]["port"]
        assert backend_port == {"number": 80} or backend_port == {"name": "http"}

        deployment = one(docs, "Deployment")
        assert deployment["spec"]["replicas"] == RENDER_CONTRACT["releases"]["staging"]["fixed_replicas"]

    def test_prod_render_contract(self) -> None:
        docs = render_release("prod", "prod")
        assert_common_resource_contract(docs, "prod", "prod")

        ingress = one(docs, "Ingress")
        assert ingress["spec"]["ingressClassName"] == "nginx"
        assert ingress["spec"]["rules"][0]["host"] == RENDER_CONTRACT["releases"]["prod"]["ingress_host"]

        hpa = one(docs, "HorizontalPodAutoscaler")
        expected_hpa = RENDER_CONTRACT["releases"]["prod"]["hpa"]
        assert hpa["spec"]["minReplicas"] == expected_hpa["minReplicas"]
        assert hpa["spec"]["maxReplicas"] == expected_hpa["maxReplicas"]
        metrics = {metric["resource"]["name"]: metric["resource"]["target"]["averageUtilization"] for metric in hpa["spec"]["metrics"]}
        assert metrics == {"cpu": expected_hpa["targetCPUUtilizationPercentage"], "memory": expected_hpa["targetMemoryUtilizationPercentage"]}


class TestGeneralization:
    def test_hidden_release_overlay_generalizes(self) -> None:
        values = {
            "namespace": "observability-qa",
            "environment": "qa",
            "replicaCount": 1,
            "serviceAccount": {"create": True, "annotations": {}},
            "config": {
                "LOG_FORMAT": "json",
                "CACHE_STRATEGY": "memory",
                "FEATURE_BANNER": "enabled",
                "LOG_LEVEL": "trace",
            },
            "secretEnv": [
                {"name": "API_TOKEN", "secretName": "podpulse-qa-runtime", "key": "apiToken"},
            ],
            "ingress": {
                "enabled": False,
                "className": "",
                "annotations": {},
                "host": "",
                "path": "/",
                "pathType": "Prefix",
            },
            "autoscaling": {
                "enabled": True,
                "minReplicas": 1,
                "maxReplicas": 3,
                "targetCPUUtilizationPercentage": 60,
                "targetMemoryUtilizationPercentage": 70,
            },
            "pdb": {"enabled": True, "minAvailable": 1},
        }
        docs = render_hidden(values)
        grouped = docs_by_kind(docs)

        assert sorted(grouped) == sorted(
            ["ConfigMap", "Deployment", "HorizontalPodAutoscaler", "PodDisruptionBudget", "Service", "ServiceAccount"]
        )
        config_map = one(docs, "ConfigMap")
        hpa = one(docs, "HorizontalPodAutoscaler")
        assert config_map["data"]["LOG_LEVEL"] == "trace"
        assert one(docs, "Deployment")["metadata"]["labels"]["platform.example.com/environment"] == "qa"
        assert hpa["spec"]["minReplicas"] == 1
        assert hpa["spec"]["maxReplicas"] == 3


class TestSchemaValidation:
    def test_schema_rejects_invalid_replica_type(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8") as tmp:
            tmp.write("replicaCount: many\n")
            tmp.flush()
            result = run(
                ["helm", "lint", str(CHART_DIR), "-f", str(CHART_DIR / "values.yaml"), "-f", tmp.name],
                check=False,
            )
        assert result.returncode != 0
        assert "replicaCount" in result.stdout + result.stderr
