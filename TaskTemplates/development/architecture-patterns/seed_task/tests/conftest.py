import contextlib
import csv
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
import requests


TESTS_ROOT = Path(__file__).resolve().parent
TEMPLATE_ROOT = TESTS_ROOT.parent
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", str(TEMPLATE_ROOT / "environment" / "workspace")))
VISIBLE_DATA_ROOT = WORKSPACE_ROOT / "data"
ALT_FIXTURE_ROOT = Path(os.environ.get("TESTS_ROOT", str(TESTS_ROOT))) / "fixtures" / "alternate_data"


def parse_time_to_seconds(value: str) -> int:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_gtfs_reference(data_root: Path) -> dict:
    gtfs_root = data_root / "gtfs"
    agency = load_csv(gtfs_root / "agency.txt")[0]
    routes = load_csv(gtfs_root / "routes.txt")
    stops = load_csv(gtfs_root / "stops.txt")
    trips = load_csv(gtfs_root / "trips.txt")
    stop_times = load_csv(gtfs_root / "stop_times.txt")
    calendars = load_csv(gtfs_root / "calendar.txt")
    calendar_dates = load_csv(gtfs_root / "calendar_dates.txt")

    route_by_id = {route["route_id"]: route for route in routes}
    stop_by_id = {stop["stop_id"]: stop for stop in stops}
    trip_by_id = {trip["trip_id"]: trip for trip in trips}
    stop_times_by_trip_id: dict[str, list[dict]] = {}
    child_stops_by_parent: dict[str, list[str]] = {}
    logical_stops: list[dict] = []
    logical_stop_by_id: dict[str, dict] = {}

    for stop in stops:
        parent_id = stop.get("parent_station") or None
        if parent_id:
            child_stops_by_parent.setdefault(parent_id, []).append(stop["stop_id"])
            continue
        logical = {
            "stop_id": stop["stop_id"],
            "stop_name": stop["stop_name"],
            "location_type": stop.get("location_type") or "0",
            "child_stop_ids": [],
        }
        logical_stops.append(logical)
        logical_stop_by_id[logical["stop_id"]] = logical

    for parent_id, children in child_stops_by_parent.items():
        if parent_id in logical_stop_by_id:
            logical_stop_by_id[parent_id]["child_stop_ids"] = sorted(children)

    for row in stop_times:
        stop_times_by_trip_id.setdefault(row["trip_id"], []).append(row)
    for rows in stop_times_by_trip_id.values():
        rows.sort(key=lambda row: int(row["stop_sequence"]))

    return {
      "agency": agency,
      "routes": routes,
      "route_by_id": route_by_id,
      "stops": stops,
      "stop_by_id": stop_by_id,
      "trips": trips,
      "trip_by_id": trip_by_id,
      "stop_times_by_trip_id": stop_times_by_trip_id,
      "logical_stops": logical_stops,
      "logical_stop_by_id": logical_stop_by_id,
      "child_stops_by_parent": child_stops_by_parent,
      "calendars": {row["service_id"]: row for row in calendars},
      "calendar_dates": calendar_dates,
    }


def service_ids_for_date(reference: dict, service_date: str) -> set[str]:
    date_digits = service_date.replace("-", "")
    weekday = time.strptime(service_date, "%Y-%m-%d").tm_wday
    weekday_key = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][weekday]
    active: set[str] = set()

    for service_id, row in reference["calendars"].items():
        if date_digits < row["start_date"] or date_digits > row["end_date"]:
            continue
        if row[weekday_key] == "1":
            active.add(service_id)

    for row in reference["calendar_dates"]:
        if row["date"] != date_digits:
            continue
        if row["exception_type"] == "1":
            active.add(row["service_id"])
        elif row["exception_type"] == "2":
            active.discard(row["service_id"])

    return active


def find_logical_stop(reference: dict, stop_id: str) -> dict | None:
    if stop_id in reference["logical_stop_by_id"]:
        return reference["logical_stop_by_id"][stop_id]
    stop = reference["stop_by_id"].get(stop_id)
    if stop and stop.get("parent_station"):
        return reference["logical_stop_by_id"].get(stop["parent_station"])
    return None


def matching_stop_ids(reference: dict, stop_id: str) -> list[str]:
    logical_stop = find_logical_stop(reference, stop_id)
    if not logical_stop:
        return []
    if logical_stop["child_stop_ids"]:
        return list(logical_stop["child_stop_ids"])
    return [logical_stop["stop_id"]]


def reference_search(reference: dict, query: str, limit: int) -> list[dict]:
    normalized = query.strip().lower()
    exact = []
    fuzzy = []
    for stop in reference["logical_stops"]:
        if stop["stop_id"].lower() == normalized:
            exact.append(stop)
        elif normalized in stop["stop_name"].lower():
            fuzzy.append(stop)
    return (exact + fuzzy)[:limit]


def reference_departures(reference: dict, stop_id: str, service_date: str, query_time: str, limit: int) -> dict:
    logical_stop = find_logical_stop(reference, stop_id)
    if not logical_stop:
      return {"stop": None, "departures": []}
    stop_ids = set(matching_stop_ids(reference, stop_id))
    query_seconds = parse_time_to_seconds(query_time)
    active_service_ids = service_ids_for_date(reference, service_date)
    departures = []
    for trip in reference["trips"]:
        if trip["service_id"] not in active_service_ids:
            continue
        for stop_time in reference["stop_times_by_trip_id"].get(trip["trip_id"], []):
            if stop_time["stop_id"] not in stop_ids:
                continue
            if parse_time_to_seconds(stop_time["departure_time"]) < query_seconds:
                continue
            route = reference["route_by_id"][trip["route_id"]]
            departures.append(
                {
                    "trip_id": trip["trip_id"],
                    "route_id": trip["route_id"],
                    "route_short_name": route["route_short_name"],
                    "route_long_name": route["route_long_name"],
                    "service_id": trip["service_id"],
                    "direction_id": trip["direction_id"],
                    "stop_id": stop_time["stop_id"],
                    "parent_stop_id": logical_stop["stop_id"],
                    "departure_time": stop_time["departure_time"],
                    "headsign": trip["trip_headsign"],
                }
            )
    departures.sort(key=lambda row: (row["departure_time"], row["route_id"], row["trip_id"]))
    return {
      "stop": logical_stop,
      "departures": departures[:limit],
    }


def reference_service_window(reference: dict, route_id: str, service_date: str) -> dict:
    active_service_ids = service_ids_for_date(reference, service_date)
    departures = []
    parent_stops: set[str] = set()
    direction_ids: set[str] = set()
    trip_count = 0

    for trip in reference["trips"]:
        if trip["route_id"] != route_id or trip["service_id"] not in active_service_ids:
            continue
        trip_count += 1
        direction_ids.add(trip["direction_id"])
        for stop_time in reference["stop_times_by_trip_id"].get(trip["trip_id"], []):
            departures.append(parse_time_to_seconds(stop_time["departure_time"]))
            stop = reference["stop_by_id"][stop_time["stop_id"]]
            parent_stops.add(stop.get("parent_station") or stop_time["stop_id"])

    route = reference["route_by_id"][route_id]
    return {
      "route": {
        "route_id": route["route_id"],
        "route_short_name": route["route_short_name"],
        "route_long_name": route["route_long_name"],
      },
      "service_window": {
        "first_departure": seconds_to_time(min(departures)) if departures else None,
        "last_departure": seconds_to_time(max(departures)) if departures else None,
        "trip_count": trip_count,
        "stop_count": len(parent_stops),
        "direction_count": len(direction_ids),
      },
    }


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def running_server(data_root: Path):
    port = find_free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["SCHEDULE_DATA_ROOT"] = str(data_root)
    env["WORKSPACE_ROOT"] = str(WORKSPACE_ROOT)
    process = subprocess.Popen(
        ["bash", str(WORKSPACE_ROOT / "scripts" / "start_server.sh")],
        cwd=WORKSPACE_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        for _ in range(80):
            try:
                response = requests.get(f"{base_url}/healthz", timeout=0.5)
                if response.ok:
                    break
            except requests.RequestException:
                time.sleep(0.1)
        else:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"server did not start\n{output}")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def run_export(data_root: Path) -> dict:
    output_path = WORKSPACE_ROOT / "output" / "schedule_snapshot.json"
    if output_path.exists():
      output_path.unlink()
    env = os.environ.copy()
    env["SCHEDULE_DATA_ROOT"] = str(data_root)
    env["WORKSPACE_ROOT"] = str(WORKSPACE_ROOT)
    subprocess.run(
        ["bash", str(WORKSPACE_ROOT / "scripts" / "export_snapshot.sh")],
        cwd=WORKSPACE_ROOT,
        env=env,
        text=True,
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def run_audit(data_root: Path, compare_root: Path | None = None) -> dict:
    output_path = WORKSPACE_ROOT / "output" / "provider_audit.json"
    if output_path.exists():
        output_path.unlink()
    env = os.environ.copy()
    env["SCHEDULE_DATA_ROOT"] = str(data_root)
    env["WORKSPACE_ROOT"] = str(WORKSPACE_ROOT)
    if compare_root is not None:
        env["SCHEDULE_AUDIT_COMPARE_ROOT"] = str(compare_root)
    else:
        env.pop("SCHEDULE_AUDIT_COMPARE_ROOT", None)
    subprocess.run(
        ["bash", str(WORKSPACE_ROOT / "scripts" / "provider_audit.sh")],
        cwd=WORKSPACE_ROOT,
        env=env,
        text=True,
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def run_compare(data_root: Path, compare_root: Path) -> dict:
    output_path = WORKSPACE_ROOT / "output" / "provider_compare.json"
    if output_path.exists():
        output_path.unlink()
    env = os.environ.copy()
    env["SCHEDULE_DATA_ROOT"] = str(data_root)
    env["SCHEDULE_COMPARE_ROOT"] = str(compare_root)
    env["WORKSPACE_ROOT"] = str(WORKSPACE_ROOT)
    subprocess.run(
        ["bash", str(WORKSPACE_ROOT / "scripts" / "provider_compare.sh")],
        cwd=WORKSPACE_ROOT,
        env=env,
        text=True,
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def build_alternate_data_root(tmp_path: Path) -> Path:
    target = tmp_path / "alternate_data"
    shutil.copytree(VISIBLE_DATA_ROOT, target)
    shutil.rmtree(target / "gtfs")
    shutil.copytree(ALT_FIXTURE_ROOT / "gtfs", target / "gtfs")
    shutil.copy2(ALT_FIXTURE_ROOT / "seed_queries.json", target / "seed_queries.json")
    return target


@pytest.fixture(scope="session")
def visible_reference() -> dict:
    return build_gtfs_reference(VISIBLE_DATA_ROOT)


@pytest.fixture(scope="session")
def visible_seed() -> dict:
    return json.loads((VISIBLE_DATA_ROOT / "seed_queries.json").read_text(encoding="utf-8"))
