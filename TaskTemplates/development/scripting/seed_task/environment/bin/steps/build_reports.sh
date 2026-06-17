#!/usr/bin/env bash
set -eu

COUNTRIES_FILE=$1
REGIONS_FILE=$2
AIRPORTS_FILE=$3
OPEN_AIRPORTS_WITH_RUNWAYS_FILE=$4
COUNTRY_OUTPUT_FILE=$5
REGION_OUTPUT_FILE=$6

python3 - "$COUNTRIES_FILE" "$REGIONS_FILE" "$AIRPORTS_FILE" "$OPEN_AIRPORTS_WITH_RUNWAYS_FILE" "$COUNTRY_OUTPUT_FILE" "$REGION_OUTPUT_FILE" <<'PY'
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

countries_file = Path(sys.argv[1])
regions_file = Path(sys.argv[2])
airports_file = Path(sys.argv[3])
open_with_runways_file = Path(sys.argv[4])
country_output_file = Path(sys.argv[5])
region_output_file = Path(sys.argv[6])

with countries_file.open(newline="", encoding="utf-8") as handle:
    countries = list(csv.DictReader(handle, delimiter="\t"))
with regions_file.open(newline="", encoding="utf-8") as handle:
    regions = list(csv.DictReader(handle, delimiter="\t"))
with airports_file.open(newline="", encoding="utf-8") as handle:
    airports = list(csv.DictReader(handle, delimiter="\t"))
with open_with_runways_file.open(newline="", encoding="utf-8") as handle:
    open_airports = list(csv.DictReader(handle, delimiter="\t"))

runway_stats = {
    row["airport_ident"]: {
        "runway_count": int(row["runway_count"] or 0),
        "longest_runway_ft": int(row["longest_runway_ft"]) if row["longest_runway_ft"] else "",
    }
    for row in open_airports
}

country_rows: list[dict[str, object]] = []
for country in sorted(countries, key=lambda row: row["country_code"]):
    country_airports = [row for row in airports if row["country_code"] == country["country_code"]]
    open_country_airports = [row for row in country_airports if row["airport_type"] != "closed"]
    longest: object = ""
    runway_count = 0
    for airport in open_country_airports:
        stats = runway_stats.get(airport["airport_ident"], {"runway_count": 0, "longest_runway_ft": ""})
        runway_count += int(stats["runway_count"])
        candidate = stats["longest_runway_ft"]
        if candidate != "" and (longest == "" or int(candidate) > int(longest)):
            longest = int(candidate)
    country_rows.append({
        "country_code": country["country_code"],
        "country_name": country["country_name"],
        "airport_count": len(country_airports),
        "open_airport_count": len(open_country_airports),
        "scheduled_open_airport_count": sum(1 for row in open_country_airports if row["scheduled_service"] == "yes"),
        "runway_count": runway_count,
        "longest_runway_ft": longest,
    })

with country_output_file.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow([
        "country_code",
        "country_name",
        "airport_count",
        "open_airport_count",
        "scheduled_open_airport_count",
        "runway_count",
        "longest_runway_ft",
    ])
    for row in country_rows:
        writer.writerow([
            row["country_code"],
            row["country_name"],
            row["airport_count"],
            row["open_airport_count"],
            row["scheduled_open_airport_count"],
            row["runway_count"],
            row["longest_runway_ft"],
        ])

region_rows: list[dict[str, object]] = []
regions_by_code = {row["region_code"]: row for row in regions}
countries_by_code = {row["country_code"]: row for row in countries}
for row in open_airports:
    region = regions_by_code[row["region_code"]]
    country = countries_by_code[row["country_code"]]
    stats = runway_stats[row["airport_ident"]]
    region_rows.append({
        "region_code": region["region_code"],
        "region_name": region["region_name"],
        "country_code": country["country_code"],
        "country_name": country["country_name"],
        "open_airport_count": 1,
        "scheduled_open_airport_count": 1 if row["scheduled_service"] == "yes" else 0,
        "runway_count": int(stats["runway_count"]),
        "longest_runway_ft": stats["longest_runway_ft"],
    })

grouped: dict[str, dict[str, object]] = {}
for row in region_rows:
    bucket = grouped.setdefault(
        row["region_code"],
        {
            "region_code": row["region_code"],
            "region_name": row["region_name"],
            "country_code": row["country_code"],
            "country_name": row["country_name"],
            "open_airport_count": 0,
            "scheduled_open_airport_count": 0,
            "runway_count": 0,
            "longest_runway_ft": "",
        },
    )
    bucket["open_airport_count"] = int(bucket["open_airport_count"]) + int(row["open_airport_count"])
    bucket["scheduled_open_airport_count"] = int(bucket["scheduled_open_airport_count"]) + int(row["scheduled_open_airport_count"])
    bucket["runway_count"] = int(bucket["runway_count"]) + int(row["runway_count"])
    candidate = row["longest_runway_ft"]
    if candidate != "" and (bucket["longest_runway_ft"] == "" or int(candidate) > int(bucket["longest_runway_ft"])):
        bucket["longest_runway_ft"] = int(candidate)

ordered_regions = sorted(
    grouped.values(),
    key=lambda row: (-int(row["scheduled_open_airport_count"]), -int(row["open_airport_count"]), row["region_code"]),
)
region_output_file.write_text(
    json.dumps({"generated_from": "ourairports", "regions": ordered_regions}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
