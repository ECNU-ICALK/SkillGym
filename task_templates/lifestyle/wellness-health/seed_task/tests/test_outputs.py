from __future__ import annotations

import csv
import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
HEALTH_URL = os.environ.get("WELLNESS_PLANNER_HEALTH_URL", "http://127.0.0.1:8147/health")
HOURLY_URL_TEMPLATE = os.environ.get(
    "WELLNESS_PLANNER_HOURLY_URL_TEMPLATE",
    "http://127.0.0.1:8147/api/conditions/hourly?date={date}",
)

MANIFEST = json.loads((DATA_DIR / "planner_manifest.json").read_text(encoding="utf-8"))
REQUESTS = list(csv.DictReader((DATA_DIR / "class_requests.csv").open(newline="", encoding="utf-8")))
VENUES = {
    row["venue_id"]: row
    for row in csv.DictReader((DATA_DIR / "venue_catalog.csv").open(newline="", encoding="utf-8"))
}
CONDITIONS = {
    hour["time_local"]: hour
    for date_local in ["2026-05-04", "2026-05-05", "2026-05-06"]
    for hour in json.loads(urllib.request.urlopen(HOURLY_URL_TEMPLATE.format(date=date_local), timeout=10).read().decode("utf-8"))["hours"]
}
POLICY = {
    "thresholds": {
        "outdoor": {
        "heat_index_c_max": 32.0,
        "us_aqi_max": 60,
        "precipitation_probability_max": 40,
    },
    "covered": {
        "heat_index_c_max": 35.0,
        "us_aqi_max": 80,
        "precipitation_probability_max": 40,
    },
        "indoor": {
            "heat_index_c_max": 999.0,
            "us_aqi_max": 999,
            "precipitation_probability_max": 100,
        },
    },
    "high_heat_sensitive_requires_indoor_at_or_above_c": 32.0,
}

ASSESSMENT_KEYS = [
    "site_id",
    "planning_window_start",
    "planning_window_end",
    "sessions",
]

SCHEDULE_COLUMNS = [
    "session_id",
    "program_day",
    "activity_name",
    "requested_start_local",
    "final_start_local",
    "final_end_local",
    "venue_id",
    "venue_name",
    "setting",
    "decision",
    "expected_attendance",
    "backup_plan",
    "notes",
]

ADVISORY_COLUMNS = [
    "session_id",
    "audience",
    "advisory_code",
    "message",
]

EXPECTED = {
    "S001": {
        "risk_level": "green",
        "allowed_decisions": {"outdoor_ok"},
        "reason_checks": [{"SAFE", "COMPLIANT", "WITHIN_LIMITS", "BELOW_THRESHOLD"}],
        "setting": "outdoor",
        "start": "2026-05-04T08:00:00-05:00",
        "end": "2026-05-04T09:00:00-05:00",
        "venue_id": "ARC_LAWN",
    },
    "S002": {
        "risk_level": "amber",
        "allowed_decisions": {"move_indoors"},
        "reason_checks": [{"AQI"}],
        "setting": "indoor",
        "start": "2026-05-04T18:00:00-05:00",
        "end": "2026-05-04T19:00:00-05:00",
        "venue_id": "ARC_STUDIO",
    },
    "S003": {
        "risk_level": {"amber", "red"},
        "allowed_decisions": {"move_indoors"},
        "reason_checks": [{"RAIN", "PRECIP", "STORM"}],
        "setting": "indoor",
        "start": "2026-05-05T17:00:00-05:00",
        "end": "2026-05-05T18:00:00-05:00",
        "venue_id": "GIVENS_STUDIO",
    },
    "S004": {
        "risk_level": {"amber", "red"},
        "allowed_decisions": {"move_indoors"},
        "reason_checks": [{"APPARENT_TEMP", "HEAT", "PRECIP", "STORM", "CAPACITY"}],
        "setting": "indoor",
        "start": "2026-05-05T17:00:00-05:00",
        "end": "2026-05-05T18:15:00-05:00",
        "venue_id": "ARC_GYM",
    },
    "S005": {
        "risk_level": {"amber", "red"},
        "allowed_decisions": {"reschedule", "move_to_lower_exposure"},
        "reason_checks": [{"APPARENT_TEMP", "HEAT"}],
        "setting": "outdoor",
        "start": "2026-05-06T09:00:00-05:00",
        "end": "2026-05-06T10:00:00-05:00",
        "venue_id": "ARC_LAWN",
    },
    "S006": {
        "risk_level": "green",
        "allowed_decisions": {"outdoor_ok"},
        "reason_checks": [{"SAFE", "COMPLIANT", "WITHIN_LIMITS", "BELOW_THRESHOLD"}],
        "setting": "outdoor",
        "start": "2026-05-06T10:00:00-05:00",
        "end": "2026-05-06T11:00:00-05:00",
        "venue_id": "BST_POOL",
    },
}


def load_json(name: str) -> dict:
    return json.loads((OUTPUT_DIR / name).read_text(encoding="utf-8"))


def load_csv(name: str) -> list[dict]:
    with (OUTPUT_DIR / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def parse_dt(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def has_reason_concepts(primary_reasons: list[str], reason_checks: list[set[str]]) -> bool:
    normalized = [reason.upper() for reason in primary_reasons]
    return all(any(any(fragment in reason for fragment in fragments) for reason in normalized) for fragments in reason_checks)


def is_safe(setting: str, audience: str, condition: dict) -> tuple[bool, str]:
    thresholds = POLICY["thresholds"][setting]
    if float(condition["precipitation_probability"]) > float(thresholds["precipitation_probability_max"]):
        return False, "RAIN_OVER_GUIDE"
    if int(condition["us_aqi"]) > int(thresholds["us_aqi_max"]):
        return False, "AQI_OVER_GUIDE"
    if float(condition["apparent_temperature_c"]) > float(thresholds["heat_index_c_max"]):
        return False, "HEAT_OVER_GUIDE"
    if audience == "high_heat_sensitive" and setting != "indoor" and float(condition["apparent_temperature_c"]) >= float(POLICY["high_heat_sensitive_requires_indoor_at_or_above_c"]):
        return False, "HEAT_OVER_GUIDE"
    return True, "SAFE_TO_KEEP"


def test_required_output_files_exist() -> None:
    for filename in [
        "session_risk_assessment.json",
        "activity_schedule.csv",
        "participant_advisories.csv",
        "operations_handoff.md",
    ]:
        assert (OUTPUT_DIR / filename).exists(), f"Missing required output file: {filename}"


def test_session_assessment_schema_and_decisions() -> None:
    payload = load_json("session_risk_assessment.json")
    assert list(payload.keys()) == ASSESSMENT_KEYS, "session_risk_assessment.json fields do not match the required schema"
    assert payload["site_id"] == MANIFEST["site_id"]
    assert payload["planning_window_start"] == MANIFEST["planning_window_start"]
    assert payload["planning_window_end"] == MANIFEST["planning_window_end"]

    sessions = payload["sessions"]
    assert isinstance(sessions, list) and len(sessions) == len(REQUESTS)
    by_id = {row["session_id"]: row for row in sessions}
    assert set(by_id) == {row["session_id"] for row in REQUESTS}

    for request in REQUESTS:
        expected = EXPECTED[request["session_id"]]
        row = by_id[request["session_id"]]
        expected_risk_levels = expected["risk_level"] if isinstance(expected["risk_level"], set) else {expected["risk_level"]}
        assert row["risk_level"] in expected_risk_levels
        assert row["decision"] in expected["allowed_decisions"]
        assert has_reason_concepts(row["primary_reasons"], expected["reason_checks"])
        assert row["recommended_setting"] == expected["setting"]
        assert row["recommended_window_start"] == expected["start"]
        assert row["recommended_window_end"] == expected["end"]


def test_activity_schedule_matches_expected_safe_plan() -> None:
    rows = load_csv("activity_schedule.csv")
    assert rows, "activity_schedule.csv is empty"
    assert list(rows[0].keys()) == SCHEDULE_COLUMNS, "activity_schedule.csv columns do not match the required schema"
    by_id = {row["session_id"]: row for row in rows}
    assert set(by_id) == set(EXPECTED)

    for request in REQUESTS:
        row = by_id[request["session_id"]]
        expected = EXPECTED[request["session_id"]]
        venue = VENUES[row["venue_id"]]
        condition = CONDITIONS[row["final_start_local"]]

        assert row["program_day"] == request["program_day"]
        assert row["activity_name"] == request["activity_name"]
        assert row["requested_start_local"] == request["requested_start_local"]
        assert row["final_start_local"] == expected["start"]
        assert row["final_end_local"] == expected["end"]
        assert row["venue_id"] == expected["venue_id"]
        assert row["venue_name"] == venue["venue_name"]
        assert row["setting"] == expected["setting"]
        assert row["decision"] in expected["allowed_decisions"]
        assert int(row["expected_attendance"]) == int(request["expected_attendance"])
        assert row["backup_plan"].strip(), f"backup_plan is empty for {request['session_id']}"
        assert row["notes"].strip(), f"notes is empty for {request['session_id']}"

        start_dt = parse_dt(row["final_start_local"])
        end_dt = parse_dt(row["final_end_local"])
        assert end_dt - start_dt == timedelta(minutes=int(request["duration_minutes"]))
        assert row["final_start_local"] in request["candidate_start_options_local"].split(";")
        assert row["venue_id"] in request["allowed_venue_ids"].split(";")
        assert request["activity_tag"] in venue["allowed_activity_tags"].split(";")
        assert int(request["expected_attendance"]) <= int(venue["capacity"])
        if request["requires_mobility_support"] == "true":
            assert venue["mobility_support"] == "true", f"{row['venue_id']} does not satisfy mobility support"
        assert venue["accessible"] == "true"

        open_hour, open_minute = map(int, venue["open_local"].split(":"))
        close_hour, close_minute = map(int, venue["close_local"].split(":"))
        opening = start_dt.replace(hour=open_hour, minute=open_minute)
        closing = start_dt.replace(hour=close_hour, minute=close_minute)
        assert opening <= start_dt < closing
        assert end_dt <= closing

        safe, _ = is_safe(row["setting"], request["audience"], condition)
        assert safe, f"Final schedule keeps an unsafe setup for {request['session_id']}"


def test_participant_advisories_cover_every_session() -> None:
    rows = load_csv("participant_advisories.csv")
    assert rows, "participant_advisories.csv is empty"
    assert list(rows[0].keys()) == ADVISORY_COLUMNS, "participant_advisories.csv columns do not match the required schema"

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["session_id"], []).append(row)
        assert row["audience"] in {"all", "outdoor_only", "high_heat_sensitive", "mobility_support"}
        assert row["advisory_code"].strip()
        assert row["message"].strip()

    assert set(grouped) == set(EXPECTED)
    for session_id, expected in EXPECTED.items():
        combined = " ".join(row["message"] for row in grouped[session_id]).lower()
        if "move_indoors" in expected["allowed_decisions"]:
            assert "indoor" in combined or "studio" in combined or "gym" in combined


def test_operations_handoff_mentions_key_changes() -> None:
    handoff = (OUTPUT_DIR / "operations_handoff.md").read_text(encoding="utf-8")
    headings = [
        "# Safety Overview",
        "# Schedule Changes",
        "# Venue Notes",
        "# Participant Advisories",
        "# Open Risks",
    ]
    cursor = 0
    for heading in headings:
        idx = handoff.find(heading, cursor)
        assert idx >= 0, f"Missing heading: {heading}"
        cursor = idx + len(heading)

    for session_id in ["S002", "S003", "S004", "S005"]:
        assert session_id in handoff, f"operations_handoff.md does not mention changed session {session_id}"

    assert "AQI" in handoff or "air quality" in handoff.lower()
    assert "heat" in handoff.lower()
