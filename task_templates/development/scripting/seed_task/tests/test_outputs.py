from __future__ import annotations

from pathlib import Path
import os
import signal
import subprocess
import tempfile
import time

from conftest import (
    ALT_FIXTURE_ROOT,
    APP_ROOT,
    DATA_ROOT,
    OUTPUT_ROOT,
    build_workspace_copy,
    compute_expected_outputs,
    load_country_csv,
    load_region_json,
    run_pipeline,
)


def wait_for_log_pattern(
    log_file: Path,
    pattern: str,
    timeout_sec: float = 10.0,
    min_mtime_ns: int | None = None,
) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if log_file.exists():
            stat = log_file.stat()
            if min_mtime_ns is not None and stat.st_mtime_ns <= min_mtime_ns:
                time.sleep(0.1)
                continue
            if pattern in log_file.read_text(encoding="utf-8", errors="replace"):
                return
        time.sleep(0.1)
    raise AssertionError(f"timed out waiting for log pattern {pattern!r} in {log_file}")


def current_log_mtime_ns(log_file: Path) -> int | None:
    if not log_file.exists():
        return None
    return log_file.stat().st_mtime_ns


def test_baseline_outputs_match_expected_contract() -> None:
    for path in OUTPUT_ROOT.glob("*"):
        if path.is_file():
            path.unlink()
    result = run_pipeline(APP_ROOT)
    assert result.returncode == 0, f"pipeline failed: {result.stderr}\n{result.stdout}"

    expected_country_rows, expected_region_payload = compute_expected_outputs(DATA_ROOT)
    actual_country_rows = load_country_csv(OUTPUT_ROOT / "country_airport_summary.csv")
    actual_region_payload = load_region_json(OUTPUT_ROOT / "region_priority_report.json")
    assert actual_country_rows == expected_country_rows
    assert actual_region_payload == expected_region_payload


def test_repeat_run_is_stable_and_log_is_current() -> None:
    first = run_pipeline(APP_ROOT)
    first_country_snapshot = (OUTPUT_ROOT / "country_airport_summary.csv").read_text(encoding="utf-8")
    first_region_snapshot = (OUTPUT_ROOT / "region_priority_report.json").read_text(encoding="utf-8")
    second = run_pipeline(APP_ROOT)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    country_snapshot = (OUTPUT_ROOT / "country_airport_summary.csv").read_text(encoding="utf-8")
    region_snapshot = (OUTPUT_ROOT / "region_priority_report.json").read_text(encoding="utf-8")
    log_text = (OUTPUT_ROOT / "rebuild.log").read_text(encoding="utf-8")

    assert country_snapshot == first_country_snapshot
    assert region_snapshot == first_region_snapshot
    assert "stage=extract_open_airports" in log_text
    assert "stage=join_runway_stats" in log_text
    assert "stage=build_reports" in log_text
    assert "status=ok" in log_text


def test_failure_returns_non_zero_and_leaves_no_final_outputs() -> None:
    workspace = build_workspace_copy(APP_ROOT)
    try:
        success = run_pipeline(workspace)
        assert success.returncode == 0, success.stderr

        broken_runways = workspace / "data" / "ourairports" / "runways.tsv"
        broken_runways.unlink()
        failed = run_pipeline(workspace)
        assert failed.returncode != 0, "missing input should fail"
        assert not (workspace / "output" / "country_airport_summary.csv").exists()
        assert not (workspace / "output" / "region_priority_report.json").exists()
    finally:
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace.parent)


def test_all_required_inputs_are_validated_and_leave_no_final_outputs() -> None:
    for filename in ["countries.tsv", "regions.tsv", "airports.tsv", "runways.tsv"]:
        workspace = build_workspace_copy(APP_ROOT)
        try:
            success = run_pipeline(workspace)
            assert success.returncode == 0, success.stderr

            broken_input = workspace / "data" / "ourairports" / filename
            broken_input.unlink()
            failed = run_pipeline(workspace)
            assert failed.returncode != 0, f"missing input should fail: {filename}"
            assert not (workspace / "output" / "country_airport_summary.csv").exists(), filename
            assert not (workspace / "output" / "region_priority_report.json").exists(), filename
        finally:
            if workspace.exists():
                import shutil

                shutil.rmtree(workspace.parent)


def test_alternate_fixture_in_space_path_matches_expected() -> None:
    workspace = build_workspace_copy(APP_ROOT, ALT_FIXTURE_ROOT)
    try:
        result = run_pipeline(workspace)
        assert result.returncode == 0, f"alternate fixture failed: {result.stderr}\n{result.stdout}"

        expected_country_rows, expected_region_payload = compute_expected_outputs(workspace / "data" / "ourairports")
        actual_country_rows = load_country_csv(workspace / "output" / "country_airport_summary.csv")
        actual_region_payload = load_region_json(workspace / "output" / "region_priority_report.json")
        assert actual_country_rows == expected_country_rows
        assert actual_region_payload == expected_region_payload
    finally:
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace.parent)


def test_custom_airports_tmp_dir_is_honored_and_cleaned() -> None:
    workspace = build_workspace_copy(APP_ROOT)
    temp_root = Path(tempfile.mkdtemp(prefix="airport tmp root "))
    requested_tmp_dir = temp_root / "shared work dir"
    try:
        result = run_pipeline(workspace, extra_env={"AIRPORTS_TMP_DIR": str(requested_tmp_dir)})
        assert result.returncode == 0, f"custom tmp dir run failed: {result.stderr}\n{result.stdout}"

        expected_country_rows, expected_region_payload = compute_expected_outputs(workspace / "data" / "ourairports")
        actual_country_rows = load_country_csv(workspace / "output" / "country_airport_summary.csv")
        actual_region_payload = load_region_json(workspace / "output" / "region_priority_report.json")
        assert actual_country_rows == expected_country_rows
        assert actual_region_payload == expected_region_payload

        assert requested_tmp_dir.exists(), "custom AIRPORTS_TMP_DIR was not used"
    finally:
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace.parent)
        if temp_root.exists():
            import shutil

            shutil.rmtree(temp_root)


def test_parallel_rebuilds_with_shared_tmp_root_and_distinct_fixtures_are_isolated() -> None:
    workspace = build_workspace_copy(APP_ROOT)
    alternate_workspace = build_workspace_copy(APP_ROOT, ALT_FIXTURE_ROOT)
    temp_root = Path(tempfile.mkdtemp(prefix="airport overlap tmp "))
    requested_tmp_dir = temp_root / "shared overlap dir"
    slow_bin = temp_root / "slow bin"
    first_run: subprocess.Popen[str] | None = None
    second_run: subprocess.Popen[str] | None = None
    try:
        slow_bin.mkdir()
        slow_sort = slow_bin / "sort"
        slow_sort.write_text(
            "#!/usr/bin/env bash\nsleep 3\nexec /usr/bin/sort \"$@\"\n",
            encoding="utf-8",
        )
        slow_sort.chmod(0o755)

        env = {
            "PATH": f"{slow_bin}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "AIRPORTS_TMP_DIR": str(requested_tmp_dir),
        }
        first_log_mtime_ns = current_log_mtime_ns(workspace / "output" / "rebuild.log")
        first_run = subprocess.Popen(
            [str(workspace / "bin" / "rebuild_airport_reports.sh")],
            cwd=str(workspace),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        wait_for_log_pattern(
            workspace / "output" / "rebuild.log",
            "stage=join_runway_stats",
            min_mtime_ns=first_log_mtime_ns,
        )
        assert first_run.poll() is None, "first rebuild finished before shared tmp overlap window was created"

        second_run = subprocess.Popen(
            [str(alternate_workspace / "bin" / "rebuild_airport_reports.sh")],
            cwd=str(alternate_workspace),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        first_stdout, first_stderr = first_run.communicate(timeout=15)
        second_stdout, second_stderr = second_run.communicate(timeout=15)

        assert first_run.returncode == 0, f"first run failed: {first_stderr}\n{first_stdout}"
        assert second_run.returncode == 0, f"second run failed: {second_stderr}\n{second_stdout}"

        expected_country_rows, expected_region_payload = compute_expected_outputs(workspace / "data" / "ourairports")
        actual_country_rows = load_country_csv(workspace / "output" / "country_airport_summary.csv")
        actual_region_payload = load_region_json(workspace / "output" / "region_priority_report.json")
        assert actual_country_rows == expected_country_rows
        assert actual_region_payload == expected_region_payload

        alternate_expected_country_rows, alternate_expected_region_payload = compute_expected_outputs(
            alternate_workspace / "data" / "ourairports"
        )
        alternate_actual_country_rows = load_country_csv(alternate_workspace / "output" / "country_airport_summary.csv")
        alternate_actual_region_payload = load_region_json(alternate_workspace / "output" / "region_priority_report.json")
        assert alternate_actual_country_rows == alternate_expected_country_rows
        assert alternate_actual_region_payload == alternate_expected_region_payload
    finally:
        if first_run is not None and first_run.poll() is None:
            first_run.kill()
            first_run.communicate(timeout=5)
        if second_run is not None and second_run.poll() is None:
            second_run.kill()
            second_run.communicate(timeout=5)
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace.parent)
        if alternate_workspace.exists():
            import shutil

            shutil.rmtree(alternate_workspace.parent)
        if temp_root.exists():
            import shutil

            shutil.rmtree(temp_root)


def test_interrupted_run_cleans_shared_tmp_root_and_allows_clean_retry() -> None:
    workspace = build_workspace_copy(APP_ROOT)
    temp_root = Path(tempfile.mkdtemp(prefix="airport interrupt tmp "))
    requested_tmp_dir = temp_root / "shared interrupt dir"
    slow_bin = temp_root / "slow bin"
    interrupted_run: subprocess.Popen[str] | None = None
    try:
        slow_bin.mkdir()
        slow_sort = slow_bin / "sort"
        slow_sort.write_text(
            "#!/usr/bin/env bash\nsleep 20\nexec /usr/bin/sort \"$@\"\n",
            encoding="utf-8",
        )
        slow_sort.chmod(0o755)

        env = {
            "PATH": f"{slow_bin}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "AIRPORTS_TMP_DIR": str(requested_tmp_dir),
        }
        log_mtime_ns = current_log_mtime_ns(workspace / "output" / "rebuild.log")
        interrupted_run = subprocess.Popen(
            [str(workspace / "bin" / "rebuild_airport_reports.sh")],
            cwd=str(workspace),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        wait_for_log_pattern(
            workspace / "output" / "rebuild.log",
            "stage=join_runway_stats",
            min_mtime_ns=log_mtime_ns,
        )
        os.killpg(interrupted_run.pid, signal.SIGTERM)
        interrupted_run.communicate(timeout=20)

        assert interrupted_run.returncode != 0, "interrupted rebuild should fail"
        assert sorted(path.name for path in (workspace / "output").iterdir()) == ["rebuild.log"]
        if requested_tmp_dir.exists():
            assert list(requested_tmp_dir.iterdir()) == []

        retry = run_pipeline(workspace, extra_env={"AIRPORTS_TMP_DIR": str(requested_tmp_dir)})
        assert retry.returncode == 0, f"retry after interruption failed: {retry.stderr}\n{retry.stdout}"
        assert sorted(path.name for path in (workspace / "output").iterdir()) == [
            "country_airport_summary.csv",
            "rebuild.log",
            "region_priority_report.json",
        ]

        expected_country_rows, expected_region_payload = compute_expected_outputs(workspace / "data" / "ourairports")
        actual_country_rows = load_country_csv(workspace / "output" / "country_airport_summary.csv")
        actual_region_payload = load_region_json(workspace / "output" / "region_priority_report.json")
        assert actual_country_rows == expected_country_rows
        assert actual_region_payload == expected_region_payload
    finally:
        if interrupted_run is not None and interrupted_run.poll() is None:
            os.killpg(interrupted_run.pid, signal.SIGKILL)
            interrupted_run.communicate(timeout=5)
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace.parent)
        if temp_root.exists():
            import shutil

            shutil.rmtree(temp_root)
