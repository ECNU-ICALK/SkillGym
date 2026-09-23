from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

import reference_review

ANSWER = reference_review.ANSWER_ROOT


def assert_numeric_close(actual: pd.Series, expected: pd.Series, atol: float, label: str) -> None:
    delta = (pd.to_numeric(actual, errors="coerce") - pd.to_numeric(expected, errors="coerce")).abs()
    assert delta.le(atol).all(), f"{label} exceeds tolerance {atol}; max diff={delta.max()}"


def normalize_iso_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="raise").dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3]


def assert_reportable_candidates_close(actual: list[dict], expected: list[dict]) -> None:
    actual_frame = pd.DataFrame(actual).sort_values("candidate_id").reset_index(drop=True)
    expected_frame = pd.DataFrame(expected).sort_values("candidate_id").reset_index(drop=True)
    assert list(actual_frame["candidate_id"]) == list(expected_frame["candidate_id"])
    assert list(actual_frame["classification"]) == list(expected_frame["classification"])
    assert list(normalize_iso_series(actual_frame["obs_time_iso"])) == list(normalize_iso_series(expected_frame["obs_time_iso"]))
    for column, tolerance in [
        ("ra_deg", 1e-9),
        ("dec_deg", 1e-9),
        ("calibrated_mag", 1e-6),
    ]:
        assert_numeric_close(actual_frame[column], expected_frame[column], tolerance, f"reportable {column}")


def test_required_outputs_exist_and_parse() -> None:
    required = [
        ANSWER / "candidate_review.ecsv",
        ANSWER / "photometry_summary.tsv",
        ANSWER / "crossmatch_audit.tsv",
        ANSWER / "triage_diagnostics.tsv",
        ANSWER / "report.json",
    ]
    for path in required:
        assert path.exists(), f"missing required output: {path}"
        assert path.stat().st_size > 0, f"empty required output: {path}"
    outputs = reference_review.read_submission()
    assert list(outputs["candidate_review"].columns) == reference_review.CANDIDATE_COLUMNS
    assert list(outputs["photometry_summary"].columns) == reference_review.PHOTOMETRY_COLUMNS
    assert list(outputs["crossmatch_audit"].columns) == reference_review.CROSSMATCH_COLUMNS
    assert list(outputs["triage_diagnostics"].columns) == reference_review.DIAGNOSTIC_COLUMNS
    assert isinstance(outputs["report"], dict)


def test_bound_astropy_skill_is_available_and_unchanged_enough() -> None:
    skill_path = Path("/root/.codex/skills/astropy/SKILL.md")
    try:
        exists = skill_path.exists()
    except PermissionError:
        return
    if not exists:
        return
    content = skill_path.read_text(encoding="utf-8")
    assert "# Astropy" in content
    assert "Converting between celestial coordinate systems" in content
    assert "WCS transformations between pixel and world coordinates" in content


def test_candidate_review_matches_oracle() -> None:
    expected = reference_review.sorted_frame(
        reference_review.build_expected_bundle()["candidate_review"],
        ["candidate_id"],
    )
    actual = reference_review.sorted_frame(
        reference_review.read_submission()["candidate_review"],
        ["candidate_id"],
    )
    assert_frame_equal(
        actual[["field_id", "candidate_id", "fits_file", "visit_id", "filter", "quality_flags", "classification", "reportable"]],
        expected[["field_id", "candidate_id", "fits_file", "visit_id", "filter", "quality_flags", "classification", "reportable"]],
        check_dtype=False,
    )
    assert list(normalize_iso_series(actual["obs_time_iso"])) == list(normalize_iso_series(expected["obs_time_iso"]))
    for column, tolerance in [
        ("x_pixel", 1e-6),
        ("y_pixel", 1e-6),
        ("ra_deg", 1e-9),
        ("dec_deg", 1e-9),
        ("gal_l_deg", 1e-8),
        ("gal_b_deg", 1e-8),
        ("obs_time_mjd", 1e-9),
        ("snr", 1e-6),
    ]:
        assert_numeric_close(actual[column], expected[column], tolerance, column)
    assert set(actual["classification"]) == {
        "extragalactic_candidate",
        "reject_foreground_star",
        "reject_low_snr",
        "reject_bad_measurement",
        "review_no_host",
        "reject_uncertain_photometry",
        "review_faint_host_association",
    }


def test_support_tables_match_oracle() -> None:
    expected_bundle = reference_review.build_expected_bundle()
    actual_bundle = reference_review.read_submission()

    expected_photo = reference_review.sorted_frame(expected_bundle["photometry_summary"], ["candidate_id"])
    actual_photo = reference_review.sorted_frame(actual_bundle["photometry_summary"], ["candidate_id"])
    assert_frame_equal(
        actual_photo[["candidate_id", "host_id"]],
        expected_photo[["candidate_id", "host_id"]],
        check_dtype=False,
    )
    for column in [
        "flux_aperture",
        "flux_err",
        "zeropoint_ab",
        "extinction_mag",
        "exposure_seconds",
        "calibrated_mag",
        "mag_unc",
        "host_redshift",
        "distance_mpc",
        "absolute_mag",
    ]:
        assert_numeric_close(actual_photo[column], expected_photo[column], 1e-6, f"photometry {column}")

    expected_cross = reference_review.sorted_frame(expected_bundle["crossmatch_audit"], ["candidate_id"])
    actual_cross = reference_review.sorted_frame(actual_bundle["crossmatch_audit"], ["candidate_id"])
    actual_cross = actual_cross.copy()
    expected_cross = expected_cross.copy()
    actual_cross["nearest_gaia_id"] = actual_cross["nearest_gaia_id"].astype(str)
    expected_cross["nearest_gaia_id"] = expected_cross["nearest_gaia_id"].astype(str)
    actual_cross["rejection_reason"] = actual_cross["rejection_reason"].fillna("")
    expected_cross["rejection_reason"] = expected_cross["rejection_reason"].fillna("")
    assert_frame_equal(
        actual_cross[["candidate_id", "nearest_gaia_id", "nearest_host_id"]],
        expected_cross[["candidate_id", "nearest_gaia_id", "nearest_host_id"]],
        check_dtype=False,
    )
    assert_numeric_close(actual_cross["gaia_sep_arcsec"], expected_cross["gaia_sep_arcsec"], 1e-6, "gaia_sep_arcsec")
    assert_numeric_close(actual_cross["host_sep_arcsec"], expected_cross["host_sep_arcsec"], 1e-6, "host_sep_arcsec")
    assert actual_cross["match_decision"].astype(str).str.len().gt(0).all()
    reportable_lookup = actual_bundle["candidate_review"].set_index("candidate_id")["reportable"].to_dict()
    for _, row in actual_cross.iterrows():
        reason = str(row["rejection_reason"]).strip()
        if not reportable_lookup[str(row["candidate_id"])]:
            assert reason != ""

    expected_diag = reference_review.sorted_frame(expected_bundle["triage_diagnostics"], ["candidate_id"])
    actual_diag = reference_review.sorted_frame(actual_bundle["triage_diagnostics"], ["candidate_id"])
    assert actual_diag["classification_priority"].equals(expected_diag["classification_priority"])
    for column in [
        "wcs_roundtrip_x_pixel",
        "wcs_roundtrip_y_pixel",
        "host_match_margin_arcsec",
    ]:
        assert_numeric_close(actual_diag[column], expected_diag[column], 1e-6, f"diagnostic {column}")
    assert_numeric_close(
        actual_diag["gaia_reject_margin_arcsec"].abs(),
        expected_diag["gaia_reject_margin_arcsec"].abs(),
        1e-6,
        "diagnostic gaia_reject_margin_arcsec",
    )


def test_report_matches_oracle_and_bundle_consistency() -> None:
    expected = reference_review.build_expected_bundle()["report"]
    actual = reference_review.read_submission()["report"]
    assert actual["field_id"] == expected["field_id"]
    assert actual["coordinate_frame"] == "ICRS"
    assert "UTC" in actual["time_scale"]
    cosmology = actual["cosmology"]
    if isinstance(cosmology, dict):
        assert cosmology.get("name") == "FlatLambdaCDM"
    else:
        assert "FlatLambdaCDM" in str(cosmology)
    assert actual["n_input_candidates"] == expected["n_input_candidates"] == 9
    assert actual["n_reportable_candidates"] == expected["n_reportable_candidates"] == 2
    assert actual["classification_summary"] == expected["classification_summary"]
    assert_reportable_candidates_close(actual["reportable_candidates"], expected["reportable_candidates"])
    assert isinstance(actual["notes"], list) and len(actual["notes"]) >= 1
