You are preparing a reproducible review bundle for a small candidate set in the M101 field. The project team has already bundled public field cutouts, detector-space candidate picks, reference catalogs, and observation metadata into the container, but the formal review deliverables have not been generated yet.

Input data is available in:
- `/root/environment/data/fits/`: field FITS cutouts with WCS headers
- `/root/environment/data/detections/`: candidate pixel locations, fluxes, flux errors, SNR values, and quality flags
- `/root/environment/data/catalogs/`: reference source and host-galaxy data
- `/root/environment/data/observations/`: observation metadata, calibration values, and task thresholds
- `/root/environment/pipeline/`: the formal pipeline entrypoint and helper files

Your task:
1. Rebuild each candidate in sky coordinates from the bundled FITS inputs and detector-space detections, then normalize the observation metadata required by the review bundle.
2. Cross-match every candidate against the bundled reference catalog and host catalog, then assign the final candidate classification and the `reportable` flag from the bundled review rules.
3. Compute the calibrated photometric quantities, host-distance context, and review diagnostics required by the bundle, keeping the scientific conventions internally consistent across all outputs.
4. Generate a complete audit trail so every candidate can be traced from detector-space inputs to final classification, nearest matches, and review metrics.
5. Make sure the formal entrypoint `python /root/environment/pipeline/build_m101_review.py --data /root/environment/data --output /root/answer` regenerates all required deliverables.

Output:
- `/root/answer/candidate_review.ecsv`
  - one row per input candidate
  - required columns:
    `field_id`, `candidate_id`, `fits_file`, `visit_id`, `filter`, `x_pixel`, `y_pixel`, `ra_deg`, `dec_deg`, `gal_l_deg`, `gal_b_deg`, `obs_time_iso`, `obs_time_mjd`, `snr`, `quality_flags`, `classification`, `reportable`
  - `classification` must be one of:
    `extragalactic_candidate`, `reject_foreground_star`, `reject_low_snr`, `reject_bad_measurement`, `review_no_host`, `reject_uncertain_photometry`, `review_faint_host_association`
  - `reportable` must be `true` or `false`
- `/root/answer/photometry_summary.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `flux_aperture`, `flux_err`, `zeropoint_ab`, `extinction_mag`, `exposure_seconds`, `calibrated_mag`, `mag_unc`, `host_id`, `host_redshift`, `distance_mpc`, `absolute_mag`
- `/root/answer/crossmatch_audit.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `nearest_gaia_id`, `gaia_sep_arcsec`, `nearest_host_id`, `host_sep_arcsec`, `match_decision`, `rejection_reason`
- `/root/answer/triage_diagnostics.tsv`
  - one row per input candidate
  - required columns:
    `candidate_id`, `wcs_roundtrip_x_pixel`, `wcs_roundtrip_y_pixel`, `gaia_reject_margin_arcsec`, `host_match_margin_arcsec`, `classification_priority`
- `/root/answer/report.json`
  - top-level keys must include:
    `field_id`, `n_input_candidates`, `n_reportable_candidates`, `coordinate_frame`, `time_scale`, `cosmology`, `classification_summary`, `reportable_candidates`, `notes`
  - `cosmology` must clearly identify the cosmology used for the host-distance calculation
  - each item in `reportable_candidates` must include:
    `candidate_id`, `ra_deg`, `dec_deg`, `obs_time_iso`, `calibrated_mag`, `classification`

Notes:
- Use the bundled inputs to generate the final deliverables. Do not hard-code candidate coordinates, match identities, classifications, counts, or summary values.
- Respect the bundled review thresholds and their precedence from `/root/environment/data/observations/review_rules.json`.
- Keep the tabular outputs and `report.json` mutually consistent. The photometry table must stay populated for every input candidate, including the host-context columns.
- Place match outcomes and rejection rationale in `crossmatch_audit.tsv`.
- If the environment includes a bundled astronomy skill payload, follow its workflow and keep the bundle conventions aligned with it.
- Do not modify the input data, tests, dependency setup, or task metadata.
- Do not skip position reconstruction, time normalization, catalog matching, photometric calibration, distance calculation, or report generation.
- The formal entrypoint must write the final outputs to `/root/answer`.
