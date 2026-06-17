from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path

from risk_utils import expected_report, load_aligned_frame, read_submission


def _walk_numbers(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk_numbers(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_numbers(nested)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)


def _walk_strings(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_strings(nested)
    elif isinstance(value, str):
        yield value


def test_input_files_were_not_modified() -> None:
    expected = Path(os.environ.get("TASK_INPUT_HASH_PATH", "/opt/arkk-risk-input.sha256"))
    input_dir = os.environ.get("TASK_INPUT_DIR", "/root/input")
    assert expected.exists(), "Missing baseline input hash file"
    current = subprocess.check_output(
        f"find {input_dir} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current.strip() == expected.read_text(encoding="utf-8").strip()


def test_output_contains_only_finite_numeric_values() -> None:
    submission = read_submission()
    numbers = list(_walk_numbers(submission))
    assert len(numbers) >= 700, "Report should contain the requested numeric metrics and stress grid"
    assert all(math.isfinite(value) for value in numbers)
    serialized = " ".join(_walk_strings(submission)).lower()
    for banned in ["todo", "placeholder", "n/a", "nan", "infinity", "inf"]:
        assert banned not in serialized


def test_tail_risk_uses_lower_tail_negative_values() -> None:
    submission = read_submission()
    expected = expected_report()
    assert submission["portfolio_metrics"]["var_95"] < 0
    assert submission["portfolio_metrics"]["cvar_95"] < submission["portfolio_metrics"]["var_95"]
    assert abs(submission["portfolio_metrics"]["var_95"] - expected["portfolio_metrics"]["var_95"]) <= 5e-4
    assert abs(submission["portfolio_metrics"]["cvar_95"] - expected["portfolio_metrics"]["cvar_95"]) <= 5e-5


def test_factor_units_were_converted_from_percent_to_decimal() -> None:
    submission = read_submission()
    regression = submission["factor_regression"]
    expected = expected_report()["factor_regression"]
    for key in ["mkt_rf", "smb", "hml", "rmw", "cma", "mom"]:
        assert abs(regression[key]) < 3.0, f"{key} loading looks like factor percent units were not converted"
        assert abs(regression[key] - expected[key]) <= 5e-5


def test_downside_beta_and_tracking_error_definitions() -> None:
    submission = read_submission()
    expected = expected_report()["relative_metrics"]
    frame = load_aligned_frame()
    assert int((frame["qqq_return"] < 0).sum()) > 400, "Downside beta should have a meaningful negative-benchmark sample"
    assert abs(submission["relative_metrics"]["downside_beta"] - expected["downside_beta"]) <= 5e-5
    assert abs(submission["relative_metrics"]["tracking_error"] - expected["tracking_error"]) <= 5e-5
