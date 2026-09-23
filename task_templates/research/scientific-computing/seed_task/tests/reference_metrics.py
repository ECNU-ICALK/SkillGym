from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from lxml import etree
from netCDF4 import Dataset, num2date

DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))

INPUT_SUMMARY_COLUMNS = [
    "dataset_name",
    "path",
    "format",
    "coverage_start",
    "coverage_end",
    "primary_dimensions_or_rows",
    "key_variables",
    "analysis_ready",
]
DATA_ISSUE_COLUMNS = [
    "issue_id",
    "dataset_name",
    "severity",
    "issue_type",
    "affected_count",
    "evidence",
    "follow_up_action",
]
DAILY_PANEL_COLUMNS = [
    "date",
    "station_id",
    "station_lat",
    "station_lon",
    "grid_lat",
    "grid_lon",
    "total_timestamp_rows",
    "distinct_utc_hours",
    "hour_coverage_ratio",
    "valid_wtmp_obs",
    "wtmp_completeness_ratio",
    "valid_wspd_obs",
    "wspd_completeness_ratio",
    "mean_buoy_wtmp_c",
    "max_wind_speed_mps",
    "oisst_sst_c",
    "oisst_anom_c",
]
CANDIDATE_COLUMNS = [
    "rank",
    "start_date",
    "end_date",
    "n_days",
    "window_mean_sst_anom_c",
    "window_mean_buoy_wtmp_c",
    "window_min_hour_coverage_ratio",
    "window_min_wtmp_completeness_ratio",
    "selection_note",
]


def cf_datetime_to_date(value) -> pd.Timestamp:
    return pd.Timestamp(year=value.year, month=value.month, day=value.day)


def round_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if column in {"station_lat", "station_lon", "grid_lat", "grid_lon"}:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(3)
        if column in {
            "hour_coverage_ratio",
            "wtmp_completeness_ratio",
            "wspd_completeness_ratio",
            "mean_buoy_wtmp_c",
            "max_wind_speed_mps",
            "oisst_sst_c",
            "oisst_anom_c",
            "window_mean_sst_anom_c",
            "window_mean_buoy_wtmp_c",
            "window_min_hour_coverage_ratio",
            "window_min_wtmp_completeness_ratio",
        }:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(6)
    return result


def load_contract(data_root: Path = DATA_ROOT) -> dict:
    return json.loads((data_root / "contracts" / "screening_contract.json").read_text(encoding="utf-8"))


def choose_metadata_file(data_root: Path, contract: dict) -> Path:
    candidates = sorted((data_root / "metadata").glob("*.xml"))
    for path in candidates:
        xml_root = etree.parse(str(path))
        station_nodes = xml_root.xpath("//station")
        if station_nodes and station_nodes[0].attrib.get("id") == contract["station"]["station_id"]:
            return path
    raise FileNotFoundError("No metadata XML matched the contract station")


def load_station_metadata(data_root: Path = DATA_ROOT, contract: dict | None = None) -> tuple[dict, Path]:
    contract = contract or load_contract(data_root)
    metadata_path = choose_metadata_file(data_root, contract)
    xml_root = etree.parse(str(metadata_path))
    station_node = xml_root.xpath("//station")[0]
    histories = station_node.xpath("./history")
    open_ended = [history for history in histories if history.attrib.get("stop", "") == ""]
    if not open_ended:
        raise ValueError("No open-ended history entry found")
    latest = max(open_ended, key=lambda history: pd.Timestamp(history.attrib["start"]))
    station_lat = float(latest.attrib["lat"])
    station_lon = float(latest.attrib["lng"])
    return (
        {
            "station_id": station_node.attrib["id"],
            "station_name": station_node.attrib["name"],
            "station_lat": station_lat,
            "station_lon": station_lon,
            "station_lon_360": station_lon + 360 if station_lon < 0 else station_lon,
            "history_count": len(histories),
            "coverage_start": min(history.attrib["start"] for history in histories),
            "selected_history_start": latest.attrib["start"],
        },
        metadata_path,
    )


def parse_buoy_file(path: Path, contract: dict) -> tuple[pd.DataFrame, dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.strip().startswith("#YY"):
            header_index = index
            break
    if header_index is None:
        raise ValueError(f"No buoy header found in {path}")

    header = lines[header_index].replace("#", "").split()
    rows: list[dict[str, str]] = []
    dropped_rows = 0
    for line in lines[header_index + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) != len(header):
            dropped_rows += 1
            continue
        rows.append(dict(zip(header, parts)))

    raw = pd.DataFrame(rows)
    for column in ["YY", "MM", "DD", "hh", "mm"]:
        raw[column] = raw[column].astype(int)
    raw["timestamp"] = pd.to_datetime(
        raw[["YY", "MM", "DD", "hh", "mm"]].rename(
            columns={"YY": "year", "MM": "month", "DD": "day", "hh": "hour", "mm": "minute"}
        ),
        utc=True,
    )
    raw["hour"] = raw["timestamp"].dt.hour
    for column in ["WSPD", "WTMP"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
        raw.loc[raw[column].isin(contract["cleaning_rules"]["missing_value_sentinels"]), column] = np.nan

    meta = {
        "header_index": header_index,
        "dropped_rows": dropped_rows,
        "parsed_rows": len(raw),
        "coverage_start": raw["timestamp"].min().date().isoformat(),
        "coverage_end": raw["timestamp"].max().date().isoformat(),
        "path": path,
    }
    return raw, meta


def choose_buoy_file(data_root: Path, contract: dict) -> tuple[pd.DataFrame, dict]:
    required_start = pd.Timestamp(contract["study_window"]["start_date"]).date()
    required_end = pd.Timestamp(contract["study_window"]["end_date"]).date()
    for path in sorted((data_root / "buoys").glob("*.txt")):
        raw, meta = parse_buoy_file(path, contract)
        coverage_start = pd.Timestamp(meta["coverage_start"]).date()
        coverage_end = pd.Timestamp(meta["coverage_end"]).date()
        if coverage_start <= required_start and coverage_end >= required_end:
            return raw, meta
    raise FileNotFoundError("No buoy extract covered the contract study window")


def build_buoy_daily(raw: pd.DataFrame, contract: dict) -> pd.DataFrame:
    expected_hours = int(contract["daily_quality_rules"]["expected_utc_hours_per_day"])
    daily = (
        raw.assign(date=raw["timestamp"].dt.date)
        .groupby("date", as_index=False)
        .agg(
            total_timestamp_rows=("timestamp", "size"),
            distinct_utc_hours=("hour", "nunique"),
            valid_wtmp_obs=("WTMP", lambda values: int(values.notna().sum())),
            valid_wspd_obs=("WSPD", lambda values: int(values.notna().sum())),
            mean_buoy_wtmp_c=("WTMP", "mean"),
            max_wind_speed_mps=("WSPD", "max"),
        )
    )
    daily["hour_coverage_ratio"] = daily["distinct_utc_hours"] / expected_hours
    daily["wtmp_completeness_ratio"] = daily["valid_wtmp_obs"] / daily["total_timestamp_rows"]
    daily["wspd_completeness_ratio"] = daily["valid_wspd_obs"] / daily["total_timestamp_rows"]
    return daily


def choose_grid_file(data_root: Path, contract: dict, station: dict) -> tuple[pd.DataFrame, dict, dict, Path]:
    required_start = pd.Timestamp(contract["study_window"]["start_date"]).date()
    required_end = pd.Timestamp(contract["study_window"]["end_date"]).date()
    required_lon = station["station_lon_360"]
    required_lat = station["station_lat"]

    for path in sorted((data_root / "grids").glob("*.nc")):
        dataset = Dataset(path)
        latitudes = dataset.variables["lat"][:]
        longitudes = dataset.variables["lon"][:]
        time_units = dataset.variables["time"].units
        time_calendar = getattr(dataset.variables["time"], "calendar", "standard")
        dates = [
            cf_datetime_to_date(num2date(value, units=time_units, calendar=time_calendar)).date()
            for value in dataset.variables["time"][:]
        ]
        coverage_start = dates[0]
        coverage_end = dates[-1]
        spatial_match = (
            float(latitudes.min()) <= required_lat <= float(latitudes.max())
            and float(longitudes.min()) <= required_lon <= float(longitudes.max())
        )
        temporal_match = coverage_start <= required_start and coverage_end >= required_end
        if not (spatial_match and temporal_match):
            dataset.close()
            continue

        lat_idx = int(np.abs(latitudes - required_lat).argmin())
        lon_idx = int(np.abs(longitudes - required_lon).argmin())
        grid_info = {"grid_lat": float(latitudes[lat_idx]), "grid_lon": float(longitudes[lon_idx])}
        point_panel = pd.DataFrame(
            {
                "date": dates,
                "oisst_sst_c": dataset.variables["sst"][:, 0, lat_idx, lon_idx].filled(np.nan),
                "oisst_anom_c": dataset.variables["anom"][:, 0, lat_idx, lon_idx].filled(np.nan),
            }
        )
        grid_shape = {
            "time": len(dataset.dimensions["time"]),
            "zlev": len(dataset.dimensions["zlev"]),
            "lat": len(dataset.dimensions["lat"]),
            "lon": len(dataset.dimensions["lon"]),
        }
        dataset.close()
        return point_panel, grid_info, grid_shape, path

    raise FileNotFoundError("No grid subset matched the contract station and study window")


def build_input_summary(
    contract: dict,
    station: dict,
    metadata_path: Path,
    buoy_meta: dict,
    grid_shape: dict,
    grid_path: Path,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset_name": "oisst_subset",
                "path": f"/root/data/grids/{grid_path.name}",
                "format": "netcdf",
                "coverage_start": contract["study_window"]["start_date"],
                "coverage_end": contract["study_window"]["end_date"],
                "primary_dimensions_or_rows": (
                    f"time={grid_shape['time']};zlev={grid_shape['zlev']};lat={grid_shape['lat']};lon={grid_shape['lon']}"
                ),
                "key_variables": "time,zlev,lat,lon,sst,anom,err,ice",
                "analysis_ready": "yes",
            },
            {
                "dataset_name": "buoy_stdmet",
                "path": f"/root/data/buoys/{buoy_meta['path'].name}",
                "format": "plain_text_table",
                "coverage_start": buoy_meta["coverage_start"],
                "coverage_end": buoy_meta["coverage_end"],
                "primary_dimensions_or_rows": f"rows={buoy_meta['parsed_rows']}",
                "key_variables": "YY,MM,DD,hh,mm,WSPD,WTMP",
                "analysis_ready": "yes",
            },
            {
                "dataset_name": "station_metadata",
                "path": f"/root/data/metadata/{metadata_path.name}",
                "format": "xml",
                "coverage_start": station["coverage_start"],
                "coverage_end": "open",
                "primary_dimensions_or_rows": f"histories={station['history_count']}",
                "key_variables": "station@id,history@start,history@stop,history@lat,history@lng",
                "analysis_ready": "yes",
            },
            {
                "dataset_name": "screening_contract",
                "path": "/root/data/contracts/screening_contract.json",
                "format": "json",
                "coverage_start": contract["study_window"]["start_date"],
                "coverage_end": contract["study_window"]["end_date"],
                "primary_dimensions_or_rows": f"keys={len(contract)}",
                "key_variables": "station,study_window,input_selection_rules,grid_selection,cleaning_rules,daily_quality_rules,window_rules,output_contract",
                "analysis_ready": "yes",
            },
        ],
        columns=INPUT_SUMMARY_COLUMNS,
    )


def build_daily_panel(
    contract: dict,
    station: dict,
    grid_info: dict,
    buoy_daily: pd.DataFrame,
    oisst_point: pd.DataFrame,
) -> pd.DataFrame:
    merged = buoy_daily.merge(oisst_point, on="date", how="inner")
    merged["date"] = pd.to_datetime(merged["date"])
    merged = merged[
        merged["date"].between(
            pd.Timestamp(contract["study_window"]["start_date"]),
            pd.Timestamp(contract["study_window"]["end_date"]),
        )
    ].copy()
    merged["station_id"] = station["station_id"]
    merged["station_lat"] = station["station_lat"]
    merged["station_lon"] = station["station_lon"]
    merged["grid_lat"] = grid_info["grid_lat"]
    merged["grid_lon"] = grid_info["grid_lon"]
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    return merged[DAILY_PANEL_COLUMNS]


def build_candidate_windows(panel: pd.DataFrame, contract: dict) -> pd.DataFrame:
    quality = contract["daily_quality_rules"]
    rules = contract["window_rules"]
    panel_dates = panel.copy()
    panel_dates["date"] = pd.to_datetime(panel_dates["date"])
    windows: list[dict[str, object]] = []
    for index in range(len(panel_dates) - int(rules["window_days"]) + 1):
        window = panel_dates.iloc[index : index + int(rules["window_days"])]
        dates = window["date"].tolist()
        if dates[-1] != dates[0] + pd.Timedelta(days=int(rules["window_days"]) - 1):
            continue
        if not window["wtmp_completeness_ratio"].ge(float(quality["min_wtmp_completeness_ratio"])).all():
            continue
        if not window["wspd_completeness_ratio"].ge(float(quality["min_wspd_completeness_ratio"])).all():
            continue
        if not window["hour_coverage_ratio"].ge(float(quality["min_hour_coverage_ratio"])).all():
            continue
        if not window["distinct_utc_hours"].ge(int(quality["min_distinct_utc_hours"])).all():
            continue
        if not window["oisst_anom_c"].gt(float(rules["min_daily_sst_anom_c"])).all():
            continue
        windows.append(
            {
                "start_date": dates[0].strftime("%Y-%m-%d"),
                "end_date": dates[-1].strftime("%Y-%m-%d"),
                "n_days": int(rules["window_days"]),
                "window_mean_sst_anom_c": float(window["oisst_anom_c"].mean()),
                "window_mean_buoy_wtmp_c": float(window["mean_buoy_wtmp_c"].mean()),
                "window_min_hour_coverage_ratio": float(window["hour_coverage_ratio"].min()),
                "window_min_wtmp_completeness_ratio": float(window["wtmp_completeness_ratio"].min()),
                "selection_note": rules["selection_note"],
            }
        )

    shortlist = pd.DataFrame(windows)
    if shortlist.empty:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS)
    shortlist = shortlist.sort_values(
        ["window_mean_sst_anom_c", "window_mean_buoy_wtmp_c", "start_date"],
        ascending=[False, False, True],
    ).head(int(rules["top_k"]))
    shortlist.insert(0, "rank", range(1, len(shortlist) + 1))
    return shortlist[CANDIDATE_COLUMNS].reset_index(drop=True)


def build_data_issues(
    raw_buoy: pd.DataFrame,
    panel: pd.DataFrame,
    candidates: pd.DataFrame,
    station: dict,
    grid_info: dict,
    contract: dict,
    buoy_meta: dict,
) -> pd.DataFrame:
    quality = contract["daily_quality_rules"]
    missing_wtmp_rows = int(raw_buoy["WTMP"].isna().sum())
    missing_wspd_rows = int(raw_buoy["WSPD"].isna().sum())
    low_quality_days = int((pd.to_numeric(panel["wtmp_completeness_ratio"]) < float(quality["min_wtmp_completeness_ratio"])).sum())
    incomplete_hour_days = int(
        (
            (pd.to_numeric(panel["hour_coverage_ratio"]) < float(quality["min_hour_coverage_ratio"]))
            | (pd.to_numeric(panel["distinct_utc_hours"]) < int(quality["min_distinct_utc_hours"]))
        ).sum()
    )
    dropped_rows = int(buoy_meta["dropped_rows"])
    return pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-001",
                "dataset_name": "buoy_stdmet",
                "severity": "warn" if dropped_rows else "info",
                "issue_type": "row_structure_drops",
                "affected_count": dropped_rows,
                "evidence": f"{dropped_rows} buoy rows were skipped because their token count did not match the detected header",
                "follow_up_action": "Keep header detection and row parsing dynamic for candidate buoy extracts.",
            },
            {
                "issue_id": "ISSUE-002",
                "dataset_name": "buoy_stdmet",
                "severity": "high",
                "issue_type": "missing_water_temperature_rows",
                "affected_count": missing_wtmp_rows,
                "evidence": f"{missing_wtmp_rows} of {len(raw_buoy)} parsed buoy rows are missing WTMP after sentinel cleanup",
                "follow_up_action": "Restrict downstream screening to windows that meet the contract completeness threshold.",
            },
            {
                "issue_id": "ISSUE-003",
                "dataset_name": "buoy_stdmet",
                "severity": "warn" if missing_wspd_rows else "info",
                "issue_type": "missing_wind_speed_rows",
                "affected_count": missing_wspd_rows,
                "evidence": f"{missing_wspd_rows} of {len(raw_buoy)} parsed buoy rows are missing WSPD after sentinel cleanup",
                "follow_up_action": "Track wind coverage in the daily panel before reusing wind maxima downstream.",
            },
            {
                "issue_id": "ISSUE-004",
                "dataset_name": "buoy_stdmet",
                "severity": "high",
                "issue_type": "daily_wtmp_completeness_failures",
                "affected_count": low_quality_days,
                "evidence": (
                    f"{low_quality_days} of {len(panel)} overlapping days fall below WTMP completeness ratio "
                    f"{float(quality['min_wtmp_completeness_ratio']):.2f}"
                ),
                "follow_up_action": "Exclude low-completeness days from candidate-window selection.",
            },
            {
                "issue_id": "ISSUE-005",
                "dataset_name": "buoy_stdmet",
                "severity": "high",
                "issue_type": "daily_hour_span_failures",
                "affected_count": incomplete_hour_days,
                "evidence": (
                    f"{incomplete_hour_days} of {len(panel)} overlapping days fall below hour coverage ratio "
                    f"{float(quality['min_hour_coverage_ratio']):.2f} or distinct-hour threshold "
                    f"{int(quality['min_distinct_utc_hours'])}"
                ),
                "follow_up_action": "Keep candidate windows limited to days that satisfy the contract hour-span rules.",
            },
            {
                "issue_id": "ISSUE-006",
                "dataset_name": "station_metadata",
                "severity": "warn",
                "issue_type": "longitude_convention_alignment",
                "affected_count": 1,
                "evidence": (
                    f"Latest open-ended history coordinates set station longitude {station['station_lon']:.3f}, "
                    f"while nearest-grid matching uses wrapped longitude {station['station_lon_360']:.3f} "
                    f"against grid longitude {grid_info['grid_lon']:.3f}"
                ),
                "follow_up_action": "Use the wrapped longitude only for grid lookup and keep the native station longitude in outputs.",
            },
            {
                "issue_id": "ISSUE-007",
                "dataset_name": "screening_contract",
                "severity": "warn",
                "issue_type": "limited_contract_eligible_windows",
                "affected_count": len(candidates),
                "evidence": f"Only {len(candidates)} windows satisfy the current shortlist thresholds",
                "follow_up_action": "Keep the shortlist contract-driven and do not backfill ineligible windows.",
            },
        ],
        columns=DATA_ISSUE_COLUMNS,
    )


def build_analysis_intake(
    contract: dict,
    station: dict,
    grid_info: dict,
    panel: pd.DataFrame,
    issues: pd.DataFrame,
    candidates: pd.DataFrame,
    metadata_path: Path,
    buoy_meta: dict,
    grid_path: Path,
) -> str:
    headings = contract["output_contract"]["analysis_intake_headings"]
    issue_lines = "\n".join(f"- {row.issue_id}: {row.evidence}" for row in issues.itertuples(index=False))
    if candidates.empty:
        candidate_lines = "- No contract-eligible windows were found."
    else:
        candidate_lines = "\n".join(
            (
                f"- Rank {row.rank}: {row.start_date} to {row.end_date} | mean anomaly {row.window_mean_sst_anom_c:.6f} "
                f"| mean buoy WTMP {row.window_mean_buoy_wtmp_c:.6f} | min hour coverage {row.window_min_hour_coverage_ratio:.6f}"
            )
            for row in candidates.itertuples(index=False)
        )
    return "\n".join(
        [
            f"# {station['station_id']} Intake Package",
            "",
            f"## {headings[0]}",
            f"- Station: {station['station_id']} ({station['station_name']})",
            f"- Selected buoy extract: {buoy_meta['path'].name}",
            f"- Selected metadata XML: {metadata_path.name}",
            f"- Selected OISST subset: {grid_path.name}",
            f"- Selected grid point: lat {grid_info['grid_lat']:.3f}, lon {grid_info['grid_lon']:.3f}",
            f"- Contract window: {contract['study_window']['start_date']} to {contract['study_window']['end_date']}",
            "",
            f"## {headings[1]}",
            "- The local intake covers one buoy text extract, one station metadata XML, one OISST netCDF subset, and one screening contract JSON.",
            "- The buoy extract requires sentinel cleanup, row-shape checks, and daily hour-span checks before screening.",
            "",
            f"## {headings[2]}",
            issue_lines,
            "",
            f"## {headings[3]}",
            f"- Overlap window: {panel['date'].min()} to {panel['date'].max()}",
            f"- Overlap days: {len(panel)}",
            "",
            f"## {headings[4]}",
            candidate_lines,
            "",
            f"## {headings[5]}",
            "- Station coordinates come from the latest open-ended history entry with the most recent start date.",
            "- The buoy parser detects the commented header dynamically and excludes malformed or non-data rows from daily metrics.",
            "- Nearest-grid matching uses wrapped longitude only for the OISST lookup; output station longitude stays in the native metadata convention.",
            "- Candidate windows are ranked by the contract thresholds and shortlist order.",
            "",
        ]
    )


def expected_bundle(data_root: Path = DATA_ROOT) -> dict[str, object]:
    contract = load_contract(data_root)
    station, metadata_path = load_station_metadata(data_root, contract)
    raw_buoy, buoy_meta = choose_buoy_file(data_root, contract)
    buoy_daily = build_buoy_daily(raw_buoy, contract)
    oisst_point, grid_info, grid_shape, grid_path = choose_grid_file(data_root, contract, station)
    input_summary = build_input_summary(contract, station, metadata_path, buoy_meta, grid_shape, grid_path)
    panel = build_daily_panel(contract, station, grid_info, buoy_daily, oisst_point)
    candidates = build_candidate_windows(panel, contract)
    issues = build_data_issues(raw_buoy, panel, candidates, station, grid_info, contract, buoy_meta)
    analysis_intake = build_analysis_intake(contract, station, grid_info, panel, issues, candidates, metadata_path, buoy_meta, grid_path)
    return {
        "input_summary": round_frame(input_summary),
        "data_issues": round_frame(issues),
        "daily_merged_panel": round_frame(panel),
        "candidate_windows": round_frame(candidates),
        "analysis_intake": analysis_intake,
    }
