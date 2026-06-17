from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

import reference_review


def test_pipeline_reads_science_inputs_and_uses_astropy() -> None:
    script = Path(reference_review.PIPELINE).read_text(encoding="utf-8")
    for token in [
        "astropy",
        "SkyCoord",
        "WCS",
        "Time",
        "FlatLambdaCDM",
        "candidate_detections.csv",
        "visit_manifest.tsv",
        "review_rules.json",
        "gaia_m101_cone.ecsv",
        "host_galaxies.tsv",
    ]:
        assert token in script, f"pipeline is missing expected token: {token}"


def test_mutating_candidate_positions_changes_sky_outputs() -> None:
    with tempfile.TemporaryDirectory(prefix="astro-mutate-det-") as tmpdir:
        data_root = Path(tmpdir) / "data"
        output_root = Path(tmpdir) / "answer"
        reference_review.copy_tree(reference_review.DATA_ROOT, data_root)
        detections = pd.read_csv(data_root / "detections" / "candidate_detections.csv")
        detections.loc[detections["candidate_id"] == "CAND-005", "x_pixel"] += 8.0
        detections.to_csv(data_root / "detections" / "candidate_detections.csv", index=False)
        reference_review.run_pipeline(data_root, output_root)
        rerun = reference_review.read_submission(output_root)["candidate_review"]
        original = reference_review.build_expected_bundle()["candidate_review"]
        merged = rerun.merge(original[["candidate_id", "ra_deg", "dec_deg"]], on="candidate_id", suffixes=("_new", "_old"))
        shifted = merged.loc[merged["candidate_id"] == "CAND-005"].iloc[0]
        assert abs(shifted["ra_deg_new"] - shifted["ra_deg_old"]) > 1e-7
        assert abs(shifted["dec_deg_new"] - shifted["dec_deg_old"]) > 1e-9


def test_mutating_thresholds_changes_classification() -> None:
    with tempfile.TemporaryDirectory(prefix="astro-mutate-threshold-") as tmpdir:
        data_root = Path(tmpdir) / "data"
        output_root = Path(tmpdir) / "answer"
        reference_review.copy_tree(reference_review.DATA_ROOT, data_root)
        config_path = data_root / "observations" / "review_rules.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["host_match_arcsec"] = 32.0
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        reference_review.run_pipeline(data_root, output_root)
        rerun = reference_review.read_submission(output_root)["candidate_review"]
        candidate = rerun.loc[rerun["candidate_id"] == "CAND-005"].iloc[0]
        assert candidate["classification"] == "review_faint_host_association"
        assert bool(candidate["reportable"]) is False


def test_mutating_host_redshift_changes_distance_driven_classification() -> None:
    with tempfile.TemporaryDirectory(prefix="astro-mutate-host-") as tmpdir:
        data_root = Path(tmpdir) / "data"
        output_root = Path(tmpdir) / "answer"
        reference_review.copy_tree(reference_review.DATA_ROOT, data_root)
        hosts = pd.read_csv(data_root / "catalogs" / "host_galaxies.tsv", sep="\t")
        hosts.loc[hosts["host_id"] == "HOST-BKG-004", "redshift"] = 0.0032
        hosts.to_csv(data_root / "catalogs" / "host_galaxies.tsv", sep="\t", index=False)
        reference_review.run_pipeline(data_root, output_root)
        photometry = reference_review.read_submission(output_root)["photometry_summary"]
        review = reference_review.read_submission(output_root)["candidate_review"]
        candidate = review.loc[review["candidate_id"] == "CAND-004"].iloc[0]
        photo = photometry.loc[photometry["candidate_id"] == "CAND-004"].iloc[0]
        assert candidate["classification"] == "extragalactic_candidate"
        assert bool(candidate["reportable"]) is True
        assert str(photo["host_id"]) == "HOST-BKG-004"
        assert float(photo["distance_mpc"]) > 11.0
