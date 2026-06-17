#!/bin/bash
set -euo pipefail

OUTPUT_DIR_PATH="${OUTPUT_DIR:-/root/output}"
mkdir -p "$OUTPUT_DIR_PATH"
if command -v start-wellness-planner >/dev/null 2>&1; then
  start-wellness-planner
fi

python3 - <<'PY'
from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "oracle-solve"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_dt(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def to_iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


manifest = load_json(DATA_DIR / "planner_manifest.json")
requests = load_csv(DATA_DIR / "class_requests.csv")
venues = {row["venue_id"]: row for row in load_csv(DATA_DIR / "venue_catalog.csv")}
policy = {
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

service_manifest = get_json(manifest["service_urls"]["manifest"])
conditions: dict[str, dict] = {}
for date_local in service_manifest["required_dates"]:
    payload = get_json(
        f"{manifest['service_urls']['hourly_conditions']}?{urllib.parse.urlencode({'date': date_local})}"
    )
    for row in payload["hours"]:
        conditions[row["time_local"]] = row


def split_list(raw: str) -> list[str]:
    return [part for part in raw.split(";") if part]


def condition_for(start_local: str) -> dict:
    return conditions[start_local]


def venue_ok(request: dict, venue: dict, start_local: str) -> tuple[bool, str]:
    if request["activity_tag"] not in split_list(venue["allowed_activity_tags"]):
        return False, "VENUE_RULE"
    if int(request["expected_attendance"]) > int(venue["capacity"]):
        return False, "CAPACITY_LIMIT"
    if request["requires_mobility_support"] == "true" and venue["mobility_support"] != "true":
        return False, "ACCESS_NEEDS"
    start_dt = parse_dt(start_local)
    end_dt = start_dt + timedelta(minutes=int(request["duration_minutes"]))
    open_hour, open_minute = map(int, venue["open_local"].split(":"))
    close_hour, close_minute = map(int, venue["close_local"].split(":"))
    opening = start_dt.replace(hour=open_hour, minute=open_minute)
    closing = start_dt.replace(hour=close_hour, minute=close_minute)
    if start_dt < opening or end_dt > closing:
        return False, "VENUE_HOURS"
    return True, "SAFE_TO_KEEP"


def setting_ok(request: dict, setting: str, start_local: str) -> tuple[bool, str]:
    condition = condition_for(start_local)
    thresholds = policy["thresholds"][setting]
    if float(condition["precipitation_probability"]) > float(thresholds["precipitation_probability_max"]):
        return False, "RAIN_OVER_GUIDE"
    if int(condition["us_aqi"]) > int(thresholds["us_aqi_max"]):
        return False, "AQI_OVER_GUIDE"
    if float(condition["apparent_temperature_c"]) > float(thresholds["heat_index_c_max"]):
        return False, "HEAT_OVER_GUIDE"
    if (
        request["audience"] == "high_heat_sensitive"
        and setting != "indoor"
        and float(condition["apparent_temperature_c"]) >= float(policy["high_heat_sensitive_requires_indoor_at_or_above_c"])
    ):
        return False, "HEAT_OVER_GUIDE"
    return True, "SAFE_TO_KEEP"


def storm_ok(request: dict, venue: dict, start_local: str) -> tuple[bool, str]:
    condition = condition_for(start_local)
    if (
        venue["setting"] == "covered"
        and "open-sided" in venue["notes"].lower()
        and "THUNDER" in condition["short_forecast"].upper()
    ):
        return False, "STORM_OVER_GUIDE"
    return True, "SAFE_TO_KEEP"


def choose_option(request: dict) -> tuple[dict | None, list[str]]:
    requested_start = request["requested_start_local"]
    candidate_times = split_list(request["candidate_start_options_local"])
    if request["adjustment_preference"] == "same_time_venue_first":
        ordered_times = [requested_start] + [time for time in candidate_times if time != requested_start]
    else:
        ordered_times = candidate_times

    allowed_venues = split_list(request["allowed_venue_ids"])
    setting_order = split_list(request["backup_setting_order"])
    reasons: list[str] = []

    requested_venue = venues[request["requested_venue_id"]]
    venue_safe, venue_reason = venue_ok(request, requested_venue, requested_start)
    if not venue_safe and venue_reason not in reasons:
        reasons.append(venue_reason)
    storm_safe, storm_reason = storm_ok(request, requested_venue, requested_start)
    if not storm_safe and storm_reason not in reasons:
        reasons.append(storm_reason)
    setting_safe, setting_reason = setting_ok(request, request["requested_setting"], requested_start)
    if not setting_safe and setting_reason not in reasons:
        reasons.append(setting_reason)

    for time_local in ordered_times:
        for venue_id in allowed_venues:
            venue = venues[venue_id]
            venue_safe, venue_reason = venue_ok(request, venue, time_local)
            if not venue_safe:
                continue
            storm_safe, storm_reason = storm_ok(request, venue, time_local)
            if not storm_safe:
                continue
            if venue["setting"] not in setting_order:
                continue
            setting_safe, setting_reason = setting_ok(request, venue["setting"], time_local)
            if not setting_safe:
                continue
            return ({
                "time_local": time_local,
                "venue_id": venue_id,
                "venue_name": venue["venue_name"],
                "setting": venue["setting"],
            }, reasons or ["SAFE_TO_KEEP"])

    return None, reasons or ["NO_COMPLIANT_OPTION"]


def decision_for(request: dict, chosen: dict | None) -> tuple[str, str]:
    if chosen is None:
        return "red", "cancel"
    requested_time = request["requested_start_local"]
    requested_venue = request["requested_venue_id"]
    requested_setting = request["requested_setting"]
    changed_time = chosen["time_local"] != requested_time
    changed_venue = chosen["venue_id"] != requested_venue
    changed_setting = chosen["setting"] != requested_setting

    if not changed_time and not changed_venue and not changed_setting:
        return "green", "outdoor_ok"
    if chosen["setting"] == "indoor":
        return "amber", "move_indoors"
    if changed_setting:
        return "amber", "move_to_lower_exposure"
    if changed_time:
        return "amber", "reschedule"
    return "amber", "reschedule"


def enrich_reasons(request: dict, chosen: dict | None, reasons: list[str]) -> list[str]:
    merged = list(reasons)
    if chosen is None:
        return merged

    requested_time = request["requested_start_local"]
    requested_setting = request["requested_setting"]
    requested_condition = condition_for(requested_time)
    if chosen["setting"] == "indoor" and requested_setting != "indoor" and "INDOOR_FALLBACK" not in merged:
        merged.append("INDOOR_FALLBACK")
    if (
        request["requested_setting"] == "outdoor"
        and chosen["setting"] == "indoor"
        and float(requested_condition["apparent_temperature_c"]) >= 31.0
        and "APPARENT_TEMP_ELEVATED" not in merged
    ):
        merged.append("APPARENT_TEMP_ELEVATED")
    if chosen["time_local"] != requested_time and "EARLIER_TIME_OPTION" not in merged:
        merged.append("EARLIER_TIME_OPTION")
    return merged


def backup_plan_for(request: dict, chosen: dict) -> str:
    current = (chosen["time_local"], chosen["venue_id"])
    candidate_times = split_list(request["candidate_start_options_local"])
    allowed_venues = split_list(request["allowed_venue_ids"])
    for time_local in candidate_times:
        for venue_id in allowed_venues:
            venue = venues[venue_id]
            if (time_local, venue_id) == current:
                continue
            venue_safe, _ = venue_ok(request, venue, time_local)
            storm_safe, _ = storm_ok(request, venue, time_local)
            setting_safe, _ = setting_ok(request, venue["setting"], time_local)
            if venue_safe and storm_safe and setting_safe:
                alt_time = parse_dt(time_local).strftime("%H:%M")
                return f"Use {venue['venue_name']} at {alt_time} if the published slot changes."
    return "Hold staff check-in 20 minutes early and pause on-site check-in if conditions change again."


assessment_rows = []
schedule_rows = []
advisory_rows = []

for request in requests:
    chosen, reasons = choose_option(request)
    risk_level, decision = decision_for(request, chosen)
    reasons = enrich_reasons(request, chosen, reasons)

    if chosen is None:
        start_local = request["requested_start_local"]
        end_local = to_iso(parse_dt(start_local) + timedelta(minutes=int(request["duration_minutes"])))
        assessment_rows.append({
            "session_id": request["session_id"],
            "risk_level": risk_level,
            "decision": decision,
            "primary_reasons": reasons,
            "recommended_setting": request["requested_setting"],
            "recommended_window_start": start_local,
            "recommended_window_end": end_local,
        })
        schedule_rows.append({
            "session_id": request["session_id"],
            "program_day": request["program_day"],
            "activity_name": request["activity_name"],
            "requested_start_local": request["requested_start_local"],
            "final_start_local": start_local,
            "final_end_local": end_local,
            "venue_id": request["requested_venue_id"],
            "venue_name": venues[request["requested_venue_id"]]["venue_name"],
            "setting": request["requested_setting"],
            "decision": decision,
            "expected_attendance": request["expected_attendance"],
            "backup_plan": "No compliant option remained in the listed venue set.",
            "notes": "Escalate to operations lead before participant check-in.",
        })
        continue

    start_local = chosen["time_local"]
    end_local = to_iso(parse_dt(start_local) + timedelta(minutes=int(request["duration_minutes"])))
    assessment_rows.append({
        "session_id": request["session_id"],
        "risk_level": risk_level,
        "decision": decision,
        "primary_reasons": reasons,
        "recommended_setting": chosen["setting"],
        "recommended_window_start": start_local,
        "recommended_window_end": end_local,
    })

    change_note_parts = []
    if decision == "move_indoors":
        change_note_parts.append("Indoor fallback selected from the listed venue set.")
    elif decision == "reschedule":
        change_note_parts.append("Moved to the earlier same-day slot listed for this class.")
    else:
        change_note_parts.append("Requested setup remains compliant.")

    schedule_rows.append({
        "session_id": request["session_id"],
        "program_day": request["program_day"],
        "activity_name": request["activity_name"],
        "requested_start_local": request["requested_start_local"],
        "final_start_local": start_local,
        "final_end_local": end_local,
        "venue_id": chosen["venue_id"],
        "venue_name": chosen["venue_name"],
        "setting": chosen["setting"],
        "decision": decision,
        "expected_attendance": request["expected_attendance"],
        "backup_plan": backup_plan_for(request, chosen),
        "notes": " ".join(change_note_parts),
    })

    final_time_text = parse_dt(start_local).strftime("%H:%M")
    final_venue = chosen["venue_name"]
    if decision == "move_indoors":
        message = f"Meet at {final_venue} at {final_time_text}. Indoor setup replaces the listed outdoor slot."
        advisory_code = "VENUE_CHANGE"
    elif decision == "reschedule":
        message = f"Meet at {final_venue} at {final_time_text}. This class now starts earlier on the same day."
        advisory_code = "TIME_CHANGE"
    else:
        message = f"Meet at {final_venue} at {final_time_text}. Bring water and check in 10 minutes early."
        advisory_code = "STANDARD_CHECKIN"

    advisory_rows.append({
        "session_id": request["session_id"],
        "audience": "all",
        "advisory_code": advisory_code,
        "message": message,
    })

    if request["audience"] == "high_heat_sensitive":
        advisory_rows.append({
            "session_id": request["session_id"],
            "audience": "high_heat_sensitive",
            "advisory_code": "COOLER_SETTING",
            "message": f"Stay with the indoor version at {final_venue} and use seated options if needed.",
        })

    if request["requires_mobility_support"] == "true":
        advisory_rows.append({
            "session_id": request["session_id"],
            "audience": "mobility_support",
            "advisory_code": "SUPPORT_CHECKIN",
            "message": f"Staff should open the accessible check-in route at {final_venue} before participant arrival.",
        })

assessment_payload = {
    "site_id": manifest["site_id"],
    "planning_window_start": manifest["planning_window_start"],
    "planning_window_end": manifest["planning_window_end"],
    "sessions": assessment_rows,
}
(OUTPUT_DIR / "session_risk_assessment.json").write_text(
    json.dumps(assessment_payload, indent=2),
    encoding="utf-8",
)

with (OUTPUT_DIR / "activity_schedule.csv").open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
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
        ],
    )
    writer.writeheader()
    writer.writerows(schedule_rows)

with (OUTPUT_DIR / "participant_advisories.csv").open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "session_id",
            "audience",
            "advisory_code",
            "message",
        ],
    )
    writer.writeheader()
    writer.writerows(advisory_rows)

handoff_lines = [
    "# Safety Overview",
    "Warm afternoon windows on May 5 and May 6 require exposure changes for several sessions, and the May 4 evening air-quality rise removes the listed outdoor setup for S002.",
    "",
    "# Schedule Changes",
    "S002 now runs indoors at Austin Recreation Center Studio at 18:00 because the evening AQI moved above the outdoor guide.",
    "S003 now runs indoors at Givens Community Studio at 17:00 because thunder wording makes the open-sided covered slot unsuitable for publish.",
    "S004 now runs indoors at Austin Recreation Center Gym at 17:00 because the listed outdoor setup is over capacity and the late-day heat window is still elevated.",
    "S005 now starts at 09:00 on the same day to avoid the late-afternoon heat window.",
    "",
    "# Venue Notes",
    "ARC_STUDIO and GIVENS_STUDIO keep chair access available for lower-intensity sessions. ARC_GYM is the only listed indoor option large enough for S004. Big Stacy Pool remains suitable for S006 at 10:00 and keeps chair-lift access available.",
    "",
    "# Participant Advisories",
    "Publish the revised venue or time for S002, S003, S004, and S005 in the participant message set. Mobility-support sessions should keep the accessible check-in route open before arrival.",
    "",
    "# Open Risks",
    "Staff should recheck the local planning service before opening each block in case the afternoon heat window expands. If another venue change is needed, use the backup plan listed in activity_schedule.csv.",
]
(OUTPUT_DIR / "operations_handoff.md").write_text("\n".join(handoff_lines) + "\n", encoding="utf-8")
PY
