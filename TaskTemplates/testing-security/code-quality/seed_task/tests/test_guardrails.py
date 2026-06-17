from __future__ import annotations

from common import (
    baseline_data_manifest,
    baseline_package_diff_hash,
    current_data_manifest,
    current_package_diff_hash,
)


def test_input_data_files_are_unchanged() -> None:
    assert current_data_manifest() == baseline_data_manifest()


def test_package_diff_stays_equal_to_the_candidate_baseline() -> None:
    assert current_package_diff_hash() == baseline_package_diff_hash()
