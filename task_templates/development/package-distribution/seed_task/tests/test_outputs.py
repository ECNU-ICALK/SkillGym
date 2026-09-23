from __future__ import annotations

from conftest import (
    dynamic_classifier_prefix,
    dynamic_license_id,
    expected_classifier_prefix,
    expected_license_lookup,
    expected_snapshot,
    list_artifacts,
    load_automation_contract,
    load_contract,
    parse_json_output,
    read_manifest,
    run_console_script,
    run_console_script_from_sdist,
    run_installed_entry_point,
    run_installed_mypy_probe,
    run_installed_root_api,
    run_installed,
    run_installed_from_sdist,
    sha256_file,
    sdist_entries,
    wheel_entries,
    wheel_metadata_text,
)


def test_release_artifacts_exist_and_manifest_has_required_shape() -> None:
    wheel, sdist = list_artifacts()
    manifest = read_manifest()

    assert wheel.name in manifest["produced_artifacts"]
    assert sdist.name in manifest["produced_artifacts"]
    assert isinstance(manifest["console_entrypoint"], str)
    assert "pkgmeta" in manifest["console_entrypoint"]
    assert isinstance(manifest["shipped_data_files"], list)
    assert isinstance(manifest["artifact_sha256"], dict)
    assert manifest["artifact_sha256"][wheel.name] == sha256_file(wheel)
    assert manifest["artifact_sha256"][sdist.name] == sha256_file(sdist)


def test_console_script_matches_contract_snapshot_and_license_lookup() -> None:
    contract = load_contract()
    snapshot_argv = contract["snapshot"]["argv"]
    code, stdout, stderr = run_console_script(snapshot_argv)
    assert code == 0, stderr
    snapshot_payload = parse_json_output(stdout, stderr)
    assert snapshot_payload == expected_snapshot(contract["snapshot"]["top_classifier_roots_limit"])

    license_argv = contract["license_lookup"]["argv"]
    code, stdout, stderr = run_console_script(license_argv)
    assert code == 0, stderr
    license_payload = parse_json_output(stdout, stderr)
    assert license_payload == expected_license_lookup(license_argv[1])


def test_module_execution_matches_contract_classifier_lookup() -> None:
    contract = load_contract()
    lookup_argv = contract["classifier_prefix_lookup"]["argv"]
    code, stdout, stderr = run_installed(["-m", "pkgmeta_kit", *lookup_argv])
    assert code == 0, stderr
    payload = parse_json_output(stdout, stderr)
    assert payload == expected_classifier_prefix(lookup_argv[1], int(lookup_argv[3]))


def test_installed_automation_entry_point_matches_snapshot_contract() -> None:
    contract = load_automation_contract()
    code, stdout, stderr = run_installed_entry_point(
        contract["entry_point_group"],
        contract["entry_point_name"],
    )
    assert code == 0, stderr
    payload = parse_json_output(stdout, stderr)
    assert payload == expected_snapshot(contract["top_classifier_roots_limit"])


def test_installed_package_root_api_matches_snapshot_contract() -> None:
    code, stdout, stderr = run_installed_root_api()
    assert code == 0, stderr
    payload = parse_json_output(stdout, stderr)
    assert payload["snapshot"] == expected_snapshot(5)
    assert payload["catalog_summary"] == expected_snapshot(5)


def test_installed_package_supports_typed_consumer() -> None:
    code, stdout, stderr = run_installed_mypy_probe()
    assert code == 0, stdout + stderr


def test_dynamic_queries_prevent_fixture_only_implementations() -> None:
    license_id = dynamic_license_id()
    code, stdout, stderr = run_console_script(["license", license_id])
    assert code == 0, stderr
    assert parse_json_output(stdout, stderr) == expected_license_lookup(license_id)

    prefix, limit = dynamic_classifier_prefix()
    code, stdout, stderr = run_installed(["-m", "pkgmeta_kit", "classifier-prefix", prefix, "--limit", str(limit)])
    assert code == 0, stderr
    assert parse_json_output(stdout, stderr) == expected_classifier_prefix(prefix, limit)


def test_source_distribution_installs_and_runs_contract_paths() -> None:
    contract = load_contract()
    automation_contract = load_automation_contract()

    snapshot_argv = contract["snapshot"]["argv"]
    code, stdout, stderr = run_console_script_from_sdist(snapshot_argv)
    assert code == 0, stderr
    assert parse_json_output(stdout, stderr) == expected_snapshot(contract["snapshot"]["top_classifier_roots_limit"])

    lookup_argv = contract["classifier_prefix_lookup"]["argv"]
    code, stdout, stderr = run_installed_from_sdist(["-m", "pkgmeta_kit", *lookup_argv])
    assert code == 0, stderr
    assert parse_json_output(stdout, stderr) == expected_classifier_prefix(lookup_argv[1], int(lookup_argv[3]))

    code, stdout, stderr = run_installed_entry_point(
        automation_contract["entry_point_group"],
        automation_contract["entry_point_name"],
        from_sdist=True,
    )
    assert code == 0, stderr
    assert parse_json_output(stdout, stderr) == expected_snapshot(automation_contract["top_classifier_roots_limit"])

    code, stdout, stderr = run_installed_root_api(from_sdist=True)
    assert code == 0, stderr
    payload = parse_json_output(stdout, stderr)
    assert payload["snapshot"] == expected_snapshot(5)
    assert payload["catalog_summary"] == expected_snapshot(5)

    code, stdout, stderr = run_installed_mypy_probe(from_sdist=True)
    assert code == 0, stdout + stderr


def test_wheel_and_sdist_include_package_source_and_catalog_data() -> None:
    wheel, sdist = list_artifacts()
    wheel_names = wheel_entries(wheel)
    sdist_names = sdist_entries(sdist)

    assert any(name.endswith("pkgmeta_kit/data/licenses.json") for name in wheel_names)
    assert any(name.endswith("pkgmeta_kit/data/trove_classifiers.py") for name in wheel_names)
    assert any(name.endswith("pkgmeta_kit/__main__.py") for name in wheel_names)
    assert any(name.endswith("pkgmeta_kit/py.typed") for name in wheel_names)
    assert any("pyproject.toml" in name for name in sdist_names)
    assert any(name.endswith("data/licenses.json") for name in sdist_names)
    assert any(name.endswith("data/trove_classifiers.py") for name in sdist_names)
    assert any(name.endswith("py.typed") for name in sdist_names)


def test_manifest_matches_wheel_metadata() -> None:
    wheel, sdist = list_artifacts()
    manifest = read_manifest()
    metadata_text = wheel_metadata_text(wheel, "METADATA")
    entrypoints_text = wheel_metadata_text(wheel, "entry_points.txt")
    wheel_names = wheel_entries(wheel)

    assert f"Name: {manifest['package_name']}" in metadata_text
    assert f"Version: {manifest['version']}" in metadata_text
    assert "Requires-Python:" in metadata_text
    assert "pkgmeta-kit" in entrypoints_text
    shipped = set(manifest["shipped_data_files"])
    assert (
        {
            "pkgmeta_kit/data/licenses.json",
            "pkgmeta_kit/data/trove_classifiers.py",
        }
        <= shipped
        or {
            "data/licenses.json",
            "data/trove_classifiers.py",
        }
        <= shipped
    )
    assert manifest["produced_artifacts"] == sorted([wheel.name, sdist.name])
    assert any(name.endswith(".dist-info/METADATA") for name in wheel_names)
