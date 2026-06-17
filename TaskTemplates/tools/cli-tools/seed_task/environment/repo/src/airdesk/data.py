from __future__ import annotations

import csv
from pathlib import Path


class AirportDataStore:
    """Read the local OurAirports snapshot and expose joined CLI views."""

    SOURCE_FILES = (
        "countries.csv",
        "regions.csv",
        "airports.csv",
        "runways.csv",
        "airport-frequencies.csv",
    )
    SUPPORTED_AIRPORT_TYPES = (
        "large_airport",
        "medium_airport",
        "small_airport",
    )

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.countries = self._read_csv("countries.csv")
        self.regions = self._read_csv("regions.csv")
        self.airports = self._read_csv("airports.csv")
        self.runways = self._read_csv("runways.csv")
        self.frequencies = self._read_csv("airport-frequencies.csv")

        self.airport_types = set(self.SUPPORTED_AIRPORT_TYPES)
        self.scoped_airports = [
            row for row in self.airports if (row.get("type") or "").strip() in self.airport_types
        ]
        self.scoped_airport_idents = {
            (row.get("ident") or "").strip().upper()
            for row in self.scoped_airports
            if row.get("ident")
        }

        self.country_by_code = {row["code"]: row for row in self.countries}
        self.region_by_code = {row["code"]: row for row in self.regions}

        self.runways_by_airport_ident: dict[str, list[dict[str, str]]] = {}
        for row in self.runways:
            ident = row.get("airport_ident", "").strip().upper()
            if ident and ident in self.scoped_airport_idents:
                self.runways_by_airport_ident.setdefault(ident, []).append(row)

        self.frequencies_by_airport_ident: dict[str, list[dict[str, str]]] = {}
        for row in self.frequencies:
            ident = row.get("airport_ident", "").strip().upper()
            if ident and ident in self.scoped_airport_idents:
                self.frequencies_by_airport_ident.setdefault(ident, []).append(row)

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"missing data file: {path}")
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def row_counts(self) -> dict[str, int]:
        return {
            "countries.csv": len(self.countries),
            "regions.csv": len(self.regions),
            "airports.csv": len(self.airports),
            "runways.csv": len(self.runways),
            "airport-frequencies.csv": len(self.frequencies),
        }

    def stats(self) -> dict[str, int]:
        return {
            "countries": len(self.countries),
            "regions": len(self.regions),
            "airports": len(self.scoped_airports),
            "runways": sum(len(rows) for rows in self.runways_by_airport_ident.values()),
            "frequencies": sum(len(rows) for rows in self.frequencies_by_airport_ident.values()),
        }

    def _longest_runway_ft(self, ident: str) -> str:
        lengths: list[int] = []
        for row in self.runways_by_airport_ident.get(ident, []):
            value = (row.get("length_ft") or "").strip()
            if value.isdigit():
                lengths.append(int(value))
        return str(max(lengths)) if lengths else ""

    def _frequency_count(self, ident: str) -> int:
        return len(self.frequencies_by_airport_ident.get(ident, []))

    def build_airport_record(self, row: dict[str, str]) -> dict[str, object]:
        ident = (row.get("ident") or "").strip().upper()
        country_code = (row.get("iso_country") or "").strip().upper()
        region_code = (row.get("iso_region") or "").strip().upper()
        country = self.country_by_code.get(country_code, {})
        region = self.region_by_code.get(region_code, {})
        iata = (row.get("iata_code") or "").strip().upper()
        local_code = (row.get("local_code") or "").strip().upper()
        return {
            "ident": ident,
            "icao": ident,
            "iata_fallback": iata or local_code or ident,
            "airport_name": row.get("name", ""),
            "country_code": country_code,
            "country_name": country.get("name", ""),
            "region_code": region_code,
            "region_name": region.get("name", ""),
            "municipality": row.get("municipality", ""),
            "airport_type": row.get("type", ""),
            "scheduled_service": row.get("scheduled_service", ""),
            "longest_runway_ft": self._longest_runway_ft(ident),
            "frequency_count": self._frequency_count(ident),
        }

    def get_airport(self, ident: str) -> dict[str, object] | None:
        wanted = ident.strip().upper()
        for row in self.scoped_airports:
            if (row.get("ident") or "").strip().upper() == wanted:
                return self.build_airport_record(row)
        return None

    def get_country_airports(self, iso_country: str, limit: int | None = None) -> list[dict[str, object]]:
        wanted = iso_country.strip().upper()
        rows = [
            self.build_airport_record(row)
            for row in self.scoped_airports
            if (row.get("iso_country") or "").strip().upper() == wanted
        ]
        rows.sort(key=lambda row: (str(row["country_code"]), str(row["ident"])))
        if limit is not None:
            rows = rows[:limit]
        return rows
