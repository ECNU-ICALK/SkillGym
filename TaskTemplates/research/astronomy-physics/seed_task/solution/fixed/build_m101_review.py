#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.cosmology import FlatLambdaCDM
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time, TimeDelta
from astropy.wcs import WCS
import astropy.units as u


REVIEW_COSMOLOGY = FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=2.725)


def midpoint_time(start_iso: str, exposure_seconds: float) -> tuple[str, float]:
    timestamp = Time(start_iso, scale="utc") + TimeDelta(exposure_seconds / 2.0, format="sec")
    return timestamp.to_value("isot", subfmt="date_hms"), float(timestamp.mjd)


def calibrated_mag(flux_aperture: float, exposure_seconds: float, zeropoint_ab: float, extinction_mag: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return zeropoint_ab - 2.5 * math.log10(flux_aperture / exposure_seconds) - extinction_mag


def magnitude_uncertainty(flux_aperture: float, flux_err: float) -> float:
    if flux_aperture <= 0:
        return float("nan")
    return 1.0857362047581294 * flux_err / flux_aperture


def classification_priority() -> dict[str, int]:
    ordered = [
        "reject_bad_measurement",
        "reject_low_snr",
        "reject_foreground_star",
        "review_no_host",
        "reject_uncertain_photometry",
        "review_faint_host_association",
        "extragalactic_candidate",
    ]
    return {name: index + 1 for index, name in enumerate(ordered)}


def classify_candidate(
    *,
    quality_flags: str,
    snr: float,
    min_snr: float,
    gaia_sep_arcsec: float,
    gaia_reject_arcsec: float,
    host_sep_arcsec: float,
    host_match_arcsec: float,
    mag_unc: float,
    max_mag_unc: float,
    absolute_mag: float,
    reportable_absolute_mag_max: float,
) -> str:
    if quality_flags != "none":
        return "reject_bad_measurement"
    if snr < min_snr:
        return "reject_low_snr"
    if gaia_sep_arcsec <= gaia_reject_arcsec:
        return "reject_foreground_star"
    if host_sep_arcsec > host_match_arcsec:
        return "review_no_host"
    if not math.isfinite(mag_unc) or mag_unc > max_mag_unc:
        return "reject_uncertain_photometry"
    if not math.isfinite(absolute_mag) or absolute_mag > reportable_absolute_mag_max:
        return "review_faint_host_association"
    return "extragalactic_candidate"


def build_bundle(data_root: Path) -> dict[str, object]:
    detections = pd.read_csv(data_root / "detections" / "candidate_detections.csv")
    visits = pd.read_csv(data_root / "observations" / "visit_manifest.tsv", sep="\t")
    config = json.loads((data_root / "observations" / "review_rules.json").read_text(encoding="utf-8"))
    gaia = Table.read(data_root / "catalogs" / "gaia_m101_cone.ecsv", format="ascii.ecsv")
    hosts = pd.read_csv(data_root / "catalogs" / "host_galaxies.tsv", sep="\t")

    visit_by_id = {row["visit_id"]: row for _, row in visits.iterrows()}
    wcs_by_file = {
        row["fits_file"]: WCS(fits.getheader(data_root / "fits" / row["fits_file"]))
        for _, row in visits.iterrows()
    }
    gaia_id_column = "gaia_id" if "gaia_id" in gaia.colnames else "source_id"
    gaia_coords = SkyCoord(ra=gaia["ra_deg"] * u.deg, dec=gaia["dec_deg"] * u.deg, frame="icrs")
    host_coords = SkyCoord(
        ra=hosts["ra_deg"].to_numpy() * u.deg,
        dec=hosts["dec_deg"].to_numpy() * u.deg,
        frame="icrs",
    )
    priority_lookup = classification_priority()

    candidate_rows: list[dict[str, object]] = []
    photometry_rows: list[dict[str, object]] = []
    crossmatch_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []

    for _, detection in detections.iterrows():
        visit = visit_by_id[str(detection["visit_id"])]
        wcs = wcs_by_file[str(detection["fits_file"])]
        sky = SkyCoord.from_pixel(float(detection["x_pixel"]), float(detection["y_pixel"]), wcs, origin=1)
        galactic = sky.galactic
        obs_time_iso, obs_time_mjd = midpoint_time(str(visit["obs_start_utc"]), float(visit["exposure_seconds"]))

        gaia_separations = sky.separation(gaia_coords).arcsec
        gaia_index = int(gaia_separations.argmin())
        gaia_sep_arcsec = float(gaia_separations[gaia_index])
        nearest_gaia_id = str(gaia[gaia_id_column][gaia_index])
        host_separations = sky.separation(host_coords).arcsec
        host_index = int(host_separations.argmin())
        host_sep_arcsec = float(host_separations[host_index])
        host_row = hosts.iloc[host_index]
        host_distance_mpc = float(REVIEW_COSMOLOGY.luminosity_distance(float(host_row["redshift"])).to_value(u.Mpc))
        host_distance_modulus = float(5 * math.log10(host_distance_mpc) + 25)

        flux_aperture = float(detection["flux_aperture"])
        flux_err = float(detection["flux_err"])
        zeropoint_ab = float(visit["zeropoint_ab"])
        extinction_mag = float(visit["extinction_mag"])
        exposure_seconds = float(visit["exposure_seconds"])
        cal_mag = calibrated_mag(flux_aperture, exposure_seconds, zeropoint_ab, extinction_mag)
        mag_unc = magnitude_uncertainty(flux_aperture, flux_err)
        absolute_mag = cal_mag - host_distance_modulus if math.isfinite(cal_mag) else float("nan")

        classification = classify_candidate(
            quality_flags=str(detection["quality_flags"]),
            snr=float(detection["snr"]),
            min_snr=float(config["min_snr"]),
            gaia_sep_arcsec=gaia_sep_arcsec,
            gaia_reject_arcsec=float(config["gaia_reject_arcsec"]),
            host_sep_arcsec=host_sep_arcsec,
            host_match_arcsec=float(config["host_match_arcsec"]),
            mag_unc=mag_unc,
            max_mag_unc=float(config["max_mag_unc"]),
            absolute_mag=absolute_mag,
            reportable_absolute_mag_max=float(config["reportable_absolute_mag_max"]),
        )
        reportable = classification == "extragalactic_candidate"

        candidate_rows.append(
            {
                "field_id": str(detection["field_id"]),
                "candidate_id": str(detection["candidate_id"]),
                "fits_file": str(detection["fits_file"]),
                "visit_id": str(detection["visit_id"]),
                "filter": str(detection["filter_name"]) if "filter_name" in detection else str(detection["filter"]),
                "x_pixel": float(detection["x_pixel"]),
                "y_pixel": float(detection["y_pixel"]),
                "ra_deg": float(sky.ra.deg),
                "dec_deg": float(sky.dec.deg),
                "gal_l_deg": float(galactic.l.deg),
                "gal_b_deg": float(galactic.b.deg),
                "obs_time_iso": obs_time_iso,
                "obs_time_mjd": obs_time_mjd,
                "snr": float(detection["snr"]),
                "quality_flags": str(detection["quality_flags"]),
                "classification": classification,
                "reportable": reportable,
            }
        )
        photometry_rows.append(
            {
                "candidate_id": str(detection["candidate_id"]),
                "flux_aperture": flux_aperture,
                "flux_err": flux_err,
                "zeropoint_ab": zeropoint_ab,
                "extinction_mag": extinction_mag,
                "exposure_seconds": exposure_seconds,
                "calibrated_mag": cal_mag,
                "mag_unc": mag_unc,
                "host_id": str(host_row["host_id"]),
                "host_redshift": float(host_row["redshift"]),
                "distance_mpc": host_distance_mpc,
                "absolute_mag": absolute_mag,
            }
        )
        crossmatch_rows.append(
            {
                "candidate_id": str(detection["candidate_id"]),
                "nearest_gaia_id": nearest_gaia_id,
                "gaia_sep_arcsec": gaia_sep_arcsec,
                "nearest_host_id": str(host_row["host_id"]),
                "host_sep_arcsec": host_sep_arcsec,
                "match_decision": (
                    "gaia_reject"
                    if gaia_sep_arcsec <= float(config["gaia_reject_arcsec"])
                    else "host_match"
                    if host_sep_arcsec <= float(config["host_match_arcsec"])
                    else "no_host_match"
                ),
                "rejection_reason": "" if reportable else classification,
            }
        )
        roundtrip_x, roundtrip_y = sky.to_pixel(wcs, origin=1)
        diagnostic_rows.append(
            {
                "candidate_id": str(detection["candidate_id"]),
                "wcs_roundtrip_x_pixel": float(roundtrip_x),
                "wcs_roundtrip_y_pixel": float(roundtrip_y),
                "gaia_reject_margin_arcsec": gaia_sep_arcsec - float(config["gaia_reject_arcsec"]),
                "host_match_margin_arcsec": float(config["host_match_arcsec"]) - host_sep_arcsec,
                "classification_priority": priority_lookup[classification],
            }
        )

    candidate_df = pd.DataFrame(candidate_rows)
    photometry_df = pd.DataFrame(photometry_rows)
    crossmatch_df = pd.DataFrame(crossmatch_rows)
    diagnostics_df = pd.DataFrame(diagnostic_rows)

    reportable_candidates = []
    photometry_by_candidate = photometry_df.set_index("candidate_id")
    for _, candidate in candidate_df[candidate_df["reportable"]].iterrows():
        reportable_candidates.append(
            {
                "candidate_id": candidate["candidate_id"],
                "ra_deg": float(candidate["ra_deg"]),
                "dec_deg": float(candidate["dec_deg"]),
                "obs_time_iso": candidate["obs_time_iso"],
                "calibrated_mag": float(photometry_by_candidate.loc[candidate["candidate_id"], "calibrated_mag"]),
                "classification": candidate["classification"],
            }
        )

    classification_summary = {
        key: int(value)
        for key, value in candidate_df["classification"].value_counts().sort_index().items()
    }
    report = {
        "field_id": str(config["field_id"]),
        "n_input_candidates": int(len(candidate_df)),
        "n_reportable_candidates": int(candidate_df["reportable"].sum()),
        "coordinate_frame": "ICRS",
        "time_scale": "UTC midpoint with companion MJD",
        "cosmology": "FlatLambdaCDM(H0=70 km s^-1 Mpc^-1, Om0=0.3, Tcmb0=2.725 K)",
        "classification_summary": classification_summary,
        "reportable_candidates": reportable_candidates,
        "notes": [
            "Detector-space candidate coordinates use the FITS 1-based convention.",
            "Host-distance quantities use the nearest bundled host-galaxy entry.",
        ],
    }

    return {
        "candidate_review": candidate_df,
        "photometry_summary": photometry_df,
        "crossmatch_audit": crossmatch_df,
        "triage_diagnostics": diagnostics_df,
        "report": report,
    }


def write_bundle(bundle: dict[str, object], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    Table.from_pandas(bundle["candidate_review"]).write(
        output_root / "candidate_review.ecsv",
        format="ascii.ecsv",
        overwrite=True,
    )
    bundle["photometry_summary"].to_csv(output_root / "photometry_summary.tsv", sep="\t", index=False)
    bundle["crossmatch_audit"].to_csv(output_root / "crossmatch_audit.tsv", sep="\t", index=False)
    bundle["triage_diagnostics"].to_csv(output_root / "triage_diagnostics.tsv", sep="\t", index=False)
    (output_root / "report.json").write_text(
        json.dumps(bundle["report"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bundle = build_bundle(Path(args.data))
    write_bundle(bundle, Path(args.output))


if __name__ == "__main__":
    main()
