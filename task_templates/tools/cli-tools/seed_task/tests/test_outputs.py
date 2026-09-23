from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


APP_ROOT = Path("/app")
DATA_ROOT = APP_ROOT / "data" / "ourairports"
CONTRACT_PATH = APP_ROOT / "data" / "contracts" / "release_contract.json"
REPO_ROOT = APP_ROOT / "workspace" / "airdesk"
OUTPUT_ROOT = APP_ROOT / "output" / "release"
COMMAND_LOG_PATH = Path("/logs/agent/command.log")
VALID_FINAL_BUILD_TARGETS = {"make package", "make release"}

EXPECTED_DATA_HASHES = {
    "airport-frequencies.csv": "15c1f8739fb59e50c618e0aa9f5b0d6e6286bb46130b4e02fc4b36e03308ebeb",
    "airports.csv": "7536e8fe64559e6f5acf6ac78475afc4d1899e63d72ba47a027cae913ddae0e6",
    "countries.csv": "36f76859b7e47cb10d6a282ae56ecbf77a5d6215e5531f4d021ff57b3e55e8c0",
    "regions.csv": "27ec72d79ef634a256770f29d7d2265483c40178d49c523f332a7f7784417d79",
    "runways.csv": "36ded19f3b896f01a03d8b8362edb5968cb8802a9fc146ab86fe1b8866897e93",
}

EXPECTED_CONTRACT_HASH = "540b9dc60fa36a2098f6801066d199af61456631595da66449525cda10c2bf01"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_count(path: Path) -> int:
    return max(0, len(path.read_text(encoding="utf-8").splitlines()) - 1)


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_manifest() -> dict:
    return json.loads((OUTPUT_ROOT / "release_manifest.json").read_text(encoding="utf-8"))


def load_smoke_expected() -> dict:
    return json.loads((OUTPUT_ROOT / "smoke_expected.json").read_text(encoding="utf-8"))


def load_command_catalog() -> str:
    return (OUTPUT_ROOT / "command_catalog.md").read_text(encoding="utf-8")


def release_env() -> dict[str, str]:
    return {
        **os.environ,
        "HARBOR_LOG_AGENT_CMDS": "0",
        "PYTHONPATH": "build/pydeps:src",
    }


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    effective_env = dict(os.environ if env is None else env)
    effective_env["HARBOR_LOG_AGENT_CMDS"] = "0"
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        env=effective_env,
    )


def load_agent_make_commands() -> list[str]:
    lines = COMMAND_LOG_PATH.read_text(encoding="utf-8").splitlines()
    commands: list[str] = []
    for line in lines:
        if "\t" not in line:
            continue
        _, command = line.split("\t", 1)
        command = command.strip()
        if command.startswith("make "):
            commands.append(command)
    return commands


def assert_subsequence(commands: list[str], expected: list[str]) -> None:
    search_start = 0
    for command in expected:
        try:
            match_index = commands.index(command, search_start)
        except ValueError as exc:
            raise AssertionError(
                f"expected workflow command {command!r} in order within {commands!r}"
            ) from exc
        search_start = match_index + 1


def find_first_index(commands: list[str], expected: str, start: int = 0) -> int:
    try:
        return commands.index(expected, start)
    except ValueError as exc:
        raise AssertionError(f"expected command {expected!r} within {commands!r}") from exc


def assert_make_discovery_workflow(commands: list[str]) -> None:
    help_index = find_first_index(commands, "make help")
    init_index = find_first_index(commands, "make python-init", help_index + 1)

    if any(target in commands[init_index + 1 :] for target in ("make check", "make release")):
        return

    tests_index = find_first_index(commands, "make python-tests", init_index + 1)
    packaging_candidates = ("make packaged-smoke", "make release-smoke", "make package", "make release")
    if any(candidate in commands[tests_index + 1 :] for candidate in packaging_candidates):
        return

    raise AssertionError(
        "expected a staged make workflow after discovery: "
        f"{commands!r}"
    )


class TestMain:
    def test_release_outputs_exist_and_match_contract(self) -> None:
        contract = load_contract()
        manifest = load_manifest()

        artifact_path = OUTPUT_ROOT / str(contract["artifact_name"])
        assert artifact_path.exists(), artifact_path
        assert (OUTPUT_ROOT / "command_catalog.md").exists()
        assert (OUTPUT_ROOT / "smoke_expected.json").exists()
        assert (OUTPUT_ROOT / "sha256sums.txt").exists()

        assert set(manifest) == {
            "package_name",
            "version",
            "artifact_name",
            "entrypoint",
            "build_target",
            "source_files",
            "source_sha256",
            "source_row_counts",
            "smoke_cases",
        }
        assert manifest["package_name"] == contract["package_name"]
        assert manifest["version"] == contract["version"]
        assert manifest["artifact_name"] == contract["artifact_name"]
        assert manifest["entrypoint"] == contract["entrypoint"]
        assert manifest["build_target"] in VALID_FINAL_BUILD_TARGETS
        assert manifest["source_files"] == contract["source_files"]
        assert manifest["smoke_cases"] == contract["smoke_cases"]

        expected_sha = {
            name: sha256_file(DATA_ROOT / name)
            for name in contract["source_files"]
        }
        expected_counts = {
            name: row_count(DATA_ROOT / name)
            for name in contract["source_files"]
        }
        assert manifest["source_sha256"] == expected_sha
        assert manifest["source_row_counts"] == expected_counts

    def test_packaged_artifact_executes_all_smoke_cases(self) -> None:
        contract = load_contract()
        smoke_expected = load_smoke_expected()
        artifact_path = OUTPUT_ROOT / str(contract["artifact_name"])
        package_dir = f"{contract['package_name']}_{contract['version']}_linux_amd64"

        with tempfile.TemporaryDirectory() as tmpdir:
            unpack_root = Path(tmpdir) / "unpacked"
            with tarfile.open(artifact_path, "r:gz") as archive:
                archive.extractall(unpack_root)

            executable = unpack_root / package_dir / "bin" / "airdesk"
            assert executable.exists(), executable

            for case in contract["smoke_cases"]:
                case_id = case["id"]
                args = case["args"]
                cmd = [str(executable)]
                if args != ["--help"]:
                    cmd.extend(["--data-dir", str(DATA_ROOT)])
                cmd.extend(args)
                proc = run(cmd)
                assert proc.returncode == 0, proc.stderr
                assert proc.stdout == smoke_expected[case_id]["stdout"]

    def test_release_rerun_is_stable(self) -> None:
        contract = load_contract()
        manifest = load_manifest()
        artifact_name = str(contract["artifact_name"])
        baseline = {
            name: sha256_file(OUTPUT_ROOT / name)
            for name in (
                artifact_name,
                "release_manifest.json",
                "smoke_expected.json",
                "sha256sums.txt",
                "command_catalog.md",
            )
        }

        proc = run(
            [
                "python3",
                "-m",
                "airdesk",
                "--data-dir",
                str(DATA_ROOT),
                "release",
                "--contract",
                str(CONTRACT_PATH),
                "--output-dir",
                str(OUTPUT_ROOT),
                "--build-target",
                manifest["build_target"],
                "--require-package-lock",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            env=release_env(),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

        rerun = {
            name: sha256_file(OUTPUT_ROOT / name)
            for name in baseline
        }
        assert rerun == baseline

    def test_command_catalog_and_checksums_are_consistent(self) -> None:
        contract = load_contract()
        catalog = load_command_catalog()
        for heading in ("# Airdesk Command Catalog", "## Build", "## Smoke checks", "## Examples"):
            assert heading in catalog
        for target in (
            "make help",
            "make python-init",
            "make python-tests",
            "make cli-smoke-tests",
            "make package",
            "make packaged-smoke",
            "make preview",
            "make release",
            "make check",
            "make clean",
        ):
            assert f"`{target}`" in catalog
        for case in contract["smoke_cases"]:
            assert isinstance(case, dict)
            rendered = "airdesk " + " ".join(str(part) for part in case["args"])
            assert f"`{rendered}`" in catalog

        expected_lines = [
            f"{sha256_file(OUTPUT_ROOT / str(contract['artifact_name']))}  {contract['artifact_name']}",
            f"{sha256_file(OUTPUT_ROOT / 'release_manifest.json')}  release_manifest.json",
            f"{sha256_file(OUTPUT_ROOT / 'smoke_expected.json')}  smoke_expected.json",
        ]
        actual_lines = (OUTPUT_ROOT / "sha256sums.txt").read_text(encoding="utf-8").splitlines()
        assert actual_lines == expected_lines

    def test_make_target_surface_and_staged_workflow(self) -> None:
        proc = run(["make", "help"], cwd=REPO_ROOT)
        assert proc.returncode == 0, proc.stderr
        for target in (
            "help",
            "all-dev",
            "python-init",
            "python-tests",
            "cli-smoke-tests",
            "package",
            "packaged-smoke",
            "preview",
            "release",
            "check",
            "clean",
        ):
            assert target in proc.stdout

        proc = run(["make", "package"], cwd=REPO_ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        package_manifest = json.loads((REPO_ROOT / "dist" / "package" / "release_manifest.json").read_text(encoding="utf-8"))
        assert package_manifest["build_target"] == "make package"

        proc = run(["make", "packaged-smoke"], cwd=REPO_ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr

        preview_dir = REPO_ROOT / "build" / "release-preview"
        if preview_dir.exists():
            shutil.rmtree(preview_dir)
        proc = run(["make", "preview"], cwd=REPO_ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        preview_manifest = json.loads((preview_dir / "release_manifest.json").read_text(encoding="utf-8"))
        assert preview_manifest["build_target"] == "make preview"

        proc = run(["make", "check"], cwd=REPO_ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr


class TestGuardrails:
    def test_inputs_unchanged(self) -> None:
        actual = {name: sha256_file(DATA_ROOT / name) for name in EXPECTED_DATA_HASHES}
        assert actual == EXPECTED_DATA_HASHES
        assert sha256_file(CONTRACT_PATH) == EXPECTED_CONTRACT_HASH

    def test_artifact_bundles_workspace_source_files(self) -> None:
        contract = load_contract()
        artifact_path = OUTPUT_ROOT / str(contract["artifact_name"])
        package_dir = f"{contract['package_name']}_{contract['version']}_linux_amd64"
        expected = {
            f"{package_dir}/lib/airdesk/__init__.py": sha256_file(REPO_ROOT / "src" / "airdesk" / "__init__.py"),
            f"{package_dir}/lib/airdesk/__main__.py": sha256_file(REPO_ROOT / "src" / "airdesk" / "__main__.py"),
            f"{package_dir}/lib/airdesk/cli.py": sha256_file(REPO_ROOT / "src" / "airdesk" / "cli.py"),
            f"{package_dir}/lib/airdesk/data.py": sha256_file(REPO_ROOT / "src" / "airdesk" / "data.py"),
            f"{package_dir}/lib/airdesk/release.py": sha256_file(REPO_ROOT / "src" / "airdesk" / "release.py"),
        }
        with tarfile.open(artifact_path, "r:gz") as archive:
            members = {member.name: member for member in archive.getmembers()}
            for name, expected_hash in expected.items():
                assert name in members, name
                payload = archive.extractfile(members[name]).read()
                assert hashlib.sha256(payload).hexdigest() == expected_hash

    def test_release_contract_override_changes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            alt_contract = load_contract()
            alt_contract["version"] = "0.4.1"
            alt_contract["artifact_name"] = "airdesk_0.4.1_linux_amd64.tar.gz"
            alt_contract["smoke_cases"] = [
                alt_contract["smoke_cases"][0],
                alt_contract["smoke_cases"][1],
                alt_contract["smoke_cases"][2],
                alt_contract["smoke_cases"][3],
                {
                    "id": "country-ca-top2-json",
                    "args": ["country", "CA", "--limit", "2", "--format", "json"],
                    "format": "json",
                },
            ]
            alt_contract_path = tmpdir_path / "alt_contract.json"
            alt_contract_path.write_text(json.dumps(alt_contract), encoding="utf-8")
            alt_output = tmpdir_path / "alt_output"

            proc = run(
                [
                    "python3",
                    "-m",
                    "airdesk",
                    "--data-dir",
                    str(DATA_ROOT),
                    "release",
                    "--contract",
                    str(alt_contract_path),
                    "--output-dir",
                    str(alt_output),
                    "--build-target",
                    "make package",
                    "--require-package-lock",
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                env=release_env(),
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            manifest = json.loads((alt_output / "release_manifest.json").read_text(encoding="utf-8"))
            smoke_expected = json.loads((alt_output / "smoke_expected.json").read_text(encoding="utf-8"))
            assert manifest["version"] == "0.4.1"
            assert manifest["artifact_name"] == "airdesk_0.4.1_linux_amd64.tar.gz"
            assert manifest["build_target"] == "make package"
            country_case = smoke_expected["country-ca-top2-json"]
            payload = json.loads(country_case["stdout"])
            assert payload["returned"] == 2
            assert payload["country_code"] == "CA"

    def test_make_discovery_workflow_was_used(self) -> None:
        assert COMMAND_LOG_PATH.exists(), COMMAND_LOG_PATH
        commands = load_agent_make_commands()
        assert_make_discovery_workflow(commands)
