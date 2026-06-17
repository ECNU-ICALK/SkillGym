from __future__ import annotations

import csv
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from playwright.sync_api import sync_playwright

APP_ROOT = Path(os.environ.get("APP_ROOT", "/app/workspace"))
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
ALT_DATA_ROOT = Path(os.environ.get("ALT_DATA_ROOT", "/app/data_alt"))
SCRIPTS_ROOT = Path(os.environ.get("SCRIPTS_ROOT", "/app/scripts"))
LOG_ROOT = Path(os.environ.get("VERIFIER_LOG_ROOT", "/logs/verifier"))
STATE_DIR = Path(os.environ.get("STATE_DIR", "/app/workspace/state"))
STATIC_HASH_PATH = Path(os.environ.get("STATIC_HASH_PATH", "/opt/fullstack-template-static-data.sha256"))
BASE_URL = "http://127.0.0.1:3000"


def parse_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_dataset(root: Path) -> dict[str, Any]:
    basics = parse_tsv(root / "title_basics_sample.tsv")
    ratings = parse_tsv(root / "title_ratings_sample.tsv")
    crews = parse_tsv(root / "title_crew_sample.tsv")
    principals = parse_tsv(root / "title_principals_sample.tsv")
    names = parse_tsv(root / "name_basics_sample.tsv")

    rating_map = {
        row["tconst"]: {
            "averageRating": float(row["averageRating"]),
            "numVotes": int(row["numVotes"]),
        }
        for row in ratings
    }
    crew_map = {
        row["tconst"]: {
            "directors": [] if row["directors"] == "" else row["directors"].split(","),
            "writers": [] if row["writers"] == "" else row["writers"].split(","),
        }
        for row in crews
    }
    name_map = {row["nconst"]: row["primaryName"] for row in names}

    principals_map: dict[str, list[dict[str, Any]]] = {}
    for row in principals:
        principals_map.setdefault(row["tconst"], []).append(
            {
                "ordering": int(row["ordering"]),
                "nconst": row["nconst"],
                "category": row["category"],
                "characters": parse_characters(row["characters"]),
            }
        )

    titles = []
    for row in basics:
        crew = crew_map[row["tconst"]]
        cast = sorted(principals_map.get(row["tconst"], []), key=lambda item: item["ordering"])
        titles.append(
            {
                "tconst": row["tconst"],
                "titleType": row["titleType"],
                "primaryTitle": row["primaryTitle"],
                "originalTitle": row["originalTitle"],
                "startYear": int(row["startYear"]),
                "endYear": None if row["endYear"] == "\\N" else int(row["endYear"]),
                "runtimeMinutes": int(row["runtimeMinutes"]) if row["runtimeMinutes"] not in {"", "\\N"} else None,
                "genres": row["genres"].split(","),
                "averageRating": rating_map[row["tconst"]]["averageRating"],
                "numVotes": rating_map[row["tconst"]]["numVotes"],
                "directors": [{"nconst": nconst, "name": name_map.get(nconst, nconst)} for nconst in crew["directors"]],
                "writers": [{"nconst": nconst, "name": name_map.get(nconst, nconst)} for nconst in crew["writers"]],
                "cast": [
                    {
                        "nconst": item["nconst"],
                        "name": name_map.get(item["nconst"], item["nconst"]),
                        "category": item["category"],
                        "characters": item["characters"],
                    }
                    for item in cast
                ],
            }
        )

    return {"titles": titles, "titleMap": {title["tconst"]: title for title in titles}}


def load_seed_entries(root: Path) -> list[dict[str, Any]]:
    seed_path = root / "shortlist_seed.json"
    if not seed_path.exists():
        return []
    return json.loads(seed_path.read_text(encoding="utf-8"))


def parse_characters(raw_value: str) -> list[str]:
    if raw_value in {"", "\\N"}:
        return []
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return [raw_value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def expected_catalog(dataset: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
    items = []
    query = str(filters.get("query", "")).strip().lower()
    title_type = str(filters.get("titleType", "")).strip()
    genre = str(filters.get("genre", "")).strip()
    min_rating = float(filters["minRating"]) if filters.get("minRating") not in ("", None) else None
    min_votes = int(filters["minVotes"]) if filters.get("minVotes") not in ("", None) else None
    year_from = int(filters["yearFrom"]) if filters.get("yearFrom") not in ("", None) else None
    year_to = int(filters["yearTo"]) if filters.get("yearTo") not in ("", None) else None
    sort = filters.get("sort", "rating_desc")
    page = int(filters.get("page", 1))
    page_size = int(filters.get("pageSize", 12))

    for title in dataset["titles"]:
        haystack = f"{title['primaryTitle']} {title['originalTitle']}".lower()
        if query and query not in haystack:
            continue
        if title_type and title["titleType"] != title_type:
            continue
        if genre and genre not in title["genres"]:
            continue
        if min_rating is not None and title["averageRating"] < min_rating:
            continue
        if min_votes is not None and title["numVotes"] < min_votes:
            continue
        if year_from is not None and title["startYear"] < year_from:
            continue
        if year_to is not None and title["startYear"] > year_to:
            continue
        items.append(title)

    sorters = {
        "rating_desc": lambda title: (-title["averageRating"], -title["numVotes"], -title["startYear"], title["primaryTitle"], title["tconst"]),
        "rating_asc": lambda title: (title["averageRating"], -title["numVotes"], title["primaryTitle"], title["tconst"]),
        "votes_desc": lambda title: (-title["numVotes"], -title["averageRating"], title["primaryTitle"], title["tconst"]),
        "year_desc": lambda title: (-title["startYear"], -title["averageRating"], title["primaryTitle"], title["tconst"]),
        "year_asc": lambda title: (title["startYear"], -title["averageRating"], title["primaryTitle"], title["tconst"]),
        "title_asc": lambda title: (title["primaryTitle"], -title["averageRating"], title["tconst"]),
    }
    items = sorted(items, key=sorters.get(sort, sorters["rating_desc"]))
    total_items = len(items)
    total_pages = max((total_items + page_size - 1) // page_size, 1)
    offset = (page - 1) * page_size
    page_items = items[offset : offset + page_size]
    return {
        "page": page,
        "pageSize": page_size,
        "totalItems": total_items,
        "totalPages": total_pages,
        "items": page_items,
    }


def extract_catalog_page(payload: dict[str, Any]) -> dict[str, Any]:
    pagination = payload.get("pagination") or {}
    filters = payload.get("filters") or {}
    return {
        "page": payload.get("page", pagination.get("page", filters.get("page"))),
        "pageSize": payload.get("pageSize", pagination.get("pageSize", filters.get("pageSize"))),
        "totalItems": payload.get(
            "totalItems",
            payload.get("total", payload.get("totalResults", pagination.get("totalItems", pagination.get("total")))),
        ),
        "totalPages": payload.get("totalPages", pagination.get("totalPages")),
        "items": payload.get("items", []),
    }


def extract_shortlist_stats(payload: dict[str, Any]) -> dict[str, Any]:
    stats = payload.get("stats") or payload.get("summary") or payload.get("overview") or payload
    counts = (
        stats.get("countsByStatus")
        or stats.get("statusCounts")
        or stats.get("byStatus")
        or payload.get("countsByStatus")
        or payload.get("statusCounts")
        or payload.get("byStatus")
        or {}
    )
    highest = stats.get("highestRated") or stats.get("topRated") or payload.get("highestRated") or payload.get("topRated")
    return {
        "totalItems": stats.get("totalItems", stats.get("total", payload.get("totalItems", payload.get("total")))),
        "countsByStatus": counts,
        "averageRating": stats.get("averageRating", payload.get("averageRating")),
        "highestRated": highest,
    }


def first_visible(*locators):
    last_error = None
    for locator in locators:
        try:
            locator.first.wait_for(timeout=5000)
            return locator.first
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise AssertionError(str(last_error) if last_error else "could not find a visible locator")


def maybe_fill_shortlist_note(page) -> None:
    with suppress(Exception):
        note_box = first_visible(
            page.get_by_role("textbox", name="Note"),
            page.locator("textarea"),
        )
        if not note_box.input_value().strip():
            note_box.fill("Verifier shortlist note")


def extract_detail_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "tconst" in payload:
        return payload
    for key in ("item", "title", "data"):
        value = payload.get(key)
        if isinstance(value, dict) and "tconst" in value:
            return value
    raise AssertionError("detail payload did not contain a title object")


def assert_sorted_by_primary_key(items: list[dict[str, Any]], sort: str) -> None:
    if len(items) < 2:
        return
    field_map: dict[str, tuple[str, bool]] = {
        "rating_desc": ("averageRating", True),
        "rating_asc": ("averageRating", False),
        "votes_desc": ("numVotes", True),
        "year_desc": ("startYear", True),
        "year_asc": ("startYear", False),
        "title_asc": ("primaryTitle", False),
        "title_desc": ("primaryTitle", True),
    }
    field, descending = field_map.get(sort, ("averageRating", True))
    normalized = ["" if item.get(field) is None else item.get(field) for item in items]
    assert normalized == sorted(normalized, reverse=descending)


def choose_filter_case(dataset: dict[str, Any]) -> dict[str, Any]:
    genres = sorted({genre for title in dataset["titles"] for genre in title["genres"]})
    for title_type in ["movie", "tvSeries", "tvMiniSeries"]:
        for genre in genres:
            filters = {
                "query": "",
                "titleType": title_type,
                "genre": genre,
                "yearFrom": "1990",
                "yearTo": "2024",
                "minRating": "7.3",
                "minVotes": "100000",
                "sort": "rating_desc",
                "page": 1,
                "pageSize": 20,
            }
            result = expected_catalog(dataset, filters)
            if result["totalItems"] >= 3:
                return filters
    raise AssertionError("could not build a stable filter case from dataset")


@dataclass
class AppRuntime:
    process: subprocess.Popen[str] | None = None

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        subprocess.run(["bash", "-lc", "fuser -k 3000/tcp 2>/dev/null || true"], check=False)

    def start(self, data_root: Path, reset_state: bool, install: bool, build: bool, log_name: str) -> None:
        self.stop()
        if reset_state:
            subprocess.run([str(SCRIPTS_ROOT / "reset_runtime_state.sh")], check=True)

        env = os.environ.copy()
        env.update(
            {
                "WORKSPACE_ROOT": str(APP_ROOT),
                "IMDB_DATA_DIR": str(data_root),
                "STATE_DIR": str(STATE_DIR),
                "PORT": "3000",
                "RUN_INSTALL": "1" if install else "0",
                "RUN_BUILD": "1" if build else "0",
                "LOG_PATH": str(LOG_ROOT / log_name),
            }
        )
        self.process = subprocess.Popen(
            [str(SCRIPTS_ROOT / "run_app.sh")],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        deadline = time.time() + 240
        while time.time() < deadline:
            if self.process.poll() is not None:
                install_log = Path("/tmp/curation-workbench-install.log").read_text(encoding="utf-8", errors="ignore") if Path("/tmp/curation-workbench-install.log").exists() else ""
                build_log = Path("/tmp/curation-workbench-build.log").read_text(encoding="utf-8", errors="ignore") if Path("/tmp/curation-workbench-build.log").exists() else ""
                app_log = (LOG_ROOT / log_name).read_text(encoding="utf-8", errors="ignore") if (LOG_ROOT / log_name).exists() else ""
                raise AssertionError(
                    "application failed to start\n"
                    f"install log:\n{install_log[-4000:]}\n"
                    f"build log:\n{build_log[-4000:]}\n"
                    f"app log:\n{app_log[-4000:]}"
                )
            try:
                response = requests.get(f"{BASE_URL}/api/health", timeout=2)
                if response.ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        install_log = Path("/tmp/curation-workbench-install.log").read_text(encoding="utf-8", errors="ignore") if Path("/tmp/curation-workbench-install.log").exists() else ""
        build_log = Path("/tmp/curation-workbench-build.log").read_text(encoding="utf-8", errors="ignore") if Path("/tmp/curation-workbench-build.log").exists() else ""
        app_log = (LOG_ROOT / log_name).read_text(encoding="utf-8", errors="ignore") if (LOG_ROOT / log_name).exists() else ""
        raise AssertionError(
            "application did not become healthy in time\n"
            f"install log:\n{install_log[-4000:]}\n"
            f"build log:\n{build_log[-4000:]}\n"
            f"app log:\n{app_log[-4000:]}"
        )


RUNTIME = AppRuntime()
DEFAULT_DATASET = load_dataset(DATA_ROOT) if (DATA_ROOT / "title_basics_sample.tsv").exists() else {"titles": [], "titleMap": {}}
ALT_DATASET = load_dataset(ALT_DATA_ROOT) if (ALT_DATA_ROOT / "title_basics_sample.tsv").exists() else {"titles": [], "titleMap": {}}
DEFAULT_SEED = load_seed_entries(DATA_ROOT) if (DATA_ROOT / "shortlist_seed.json").exists() else []


def test_bootstrap_and_health() -> None:
    RUNTIME.start(DATA_ROOT, reset_state=True, install=True, build=True, log_name="default-start.log")
    response = requests.get(f"{BASE_URL}/api/health", timeout=5)
    payload = response.json()
    assert response.status_code == 200
    assert payload.get("ok") is True or payload.get("status") == "ok"
    assert payload.get("titleCount", payload.get("titles", payload.get("catalogSize"))) == len(DEFAULT_DATASET["titles"])
    assert payload.get("shortlistCount", payload.get("shortlistSize")) in {0, len(DEFAULT_SEED)}


def test_nextjs_app_router_scaffold() -> None:
    package_path = APP_ROOT / "package.json"
    tsconfig_path = APP_ROOT / "tsconfig.json"
    next_env_path = APP_ROOT / "next-env.d.ts"
    next_config_path = APP_ROOT / "next.config.ts"
    src_app_path = APP_ROOT / "src" / "app"
    required_paths = [
        src_app_path / "layout.tsx",
        src_app_path / "page.tsx",
        src_app_path / "titles" / "[tconst]" / "page.tsx",
        src_app_path / "shortlist" / "page.tsx",
        src_app_path / "api" / "health" / "route.ts",
        src_app_path / "api" / "titles" / "route.ts",
        src_app_path / "api" / "titles" / "[tconst]" / "route.ts",
        src_app_path / "api" / "shortlist" / "route.ts",
        src_app_path / "api" / "shortlist" / "[tconst]" / "route.ts",
    ]

    assert package_path.exists(), "missing package.json"
    assert tsconfig_path.exists(), "missing tsconfig.json"
    assert next_env_path.exists(), "missing next-env.d.ts"
    assert next_config_path.exists(), "missing next.config.ts"
    assert src_app_path.exists(), "missing src/app directory"
    for path in required_paths:
        assert path.exists(), f"missing required Next.js route file: {path.relative_to(APP_ROOT)}"

    package_payload = json.loads(package_path.read_text(encoding="utf-8"))
    scripts = package_payload.get("scripts", {})
    dependencies = package_payload.get("dependencies", {})
    assert "next" in dependencies and "react" in dependencies and "react-dom" in dependencies
    assert "next build" in str(scripts.get("build", ""))
    assert "next start" in str(scripts.get("start", ""))


def test_catalog_query_contract() -> None:
    filters = choose_filter_case(DEFAULT_DATASET)
    expected = expected_catalog(DEFAULT_DATASET, filters)
    response = requests.get(f"{BASE_URL}/api/titles", params=filters, timeout=5)
    payload = response.json()
    page_payload = extract_catalog_page(payload)
    assert response.status_code == 200
    assert page_payload["page"] == expected["page"]
    assert page_payload["pageSize"] == expected["pageSize"]
    assert page_payload["totalItems"] == expected["totalItems"]
    assert page_payload["totalPages"] == expected["totalPages"]
    assert {item["tconst"] for item in page_payload["items"]} == {item["tconst"] for item in expected["items"]}
    assert_sorted_by_primary_key(page_payload["items"], filters["sort"])
    assert all(isinstance(item["genres"], list) and item["genres"] for item in page_payload["items"])


def test_detail_contract() -> None:
    title = max(DEFAULT_DATASET["titles"], key=lambda item: (item["averageRating"], item["numVotes"]))
    response = requests.get(f"{BASE_URL}/api/titles/{title['tconst']}", timeout=5)
    detail_payload = extract_detail_payload(response.json())
    assert response.status_code == 200
    assert detail_payload["tconst"] == title["tconst"]
    assert detail_payload["primaryTitle"] == title["primaryTitle"]
    assert detail_payload["originalTitle"] == title["originalTitle"]
    assert detail_payload["titleType"] == title["titleType"]
    assert detail_payload["startYear"] == title["startYear"]
    assert detail_payload["genres"] == title["genres"]
    assert detail_payload["numVotes"] == title["numVotes"]


def test_shortlist_api_persistence() -> None:
    titles = sorted(DEFAULT_DATASET["titles"], key=lambda item: (-item["numVotes"], item["tconst"]))[:2]
    first, second = titles
    initial_payload = requests.get(f"{BASE_URL}/api/shortlist", timeout=5).json()
    initial_stats = extract_shortlist_stats(initial_payload)
    initial_counts = dict(initial_stats["countsByStatus"])

    first_response = requests.post(
        f"{BASE_URL}/api/shortlist",
        json={"tconst": first["tconst"], "priority": "P1", "status": "review", "note": "Priority review"},
        timeout=5,
    )
    second_response = requests.post(
        f"{BASE_URL}/api/shortlist",
        json={"tconst": second["tconst"], "priority": "P2", "status": "watch", "note": "Queue for screening"},
        timeout=5,
    )
    patch_response = requests.patch(
        f"{BASE_URL}/api/shortlist/{second['tconst']}",
        json={"priority": "P3", "status": "approve", "note": "Approved for next slate review"},
        timeout=5,
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert patch_response.status_code == 200

    before_restart = requests.get(f"{BASE_URL}/api/shortlist", timeout=5).json()
    before_stats = extract_shortlist_stats(before_restart)
    assert before_stats["totalItems"] == initial_stats["totalItems"] + 2
    assert before_stats["countsByStatus"].get("review", 0) == initial_counts.get("review", 0) + 1
    assert before_stats["countsByStatus"].get("approve", 0) == initial_counts.get("approve", 0) + 1
    assert before_stats["highestRated"] is not None

    RUNTIME.start(DATA_ROOT, reset_state=False, install=False, build=False, log_name="restart-default.log")
    after_restart = requests.get(f"{BASE_URL}/api/shortlist", timeout=5).json()
    after_stats = extract_shortlist_stats(after_restart)
    assert after_stats["totalItems"] == initial_stats["totalItems"] + 2
    assert {first["tconst"], second["tconst"]}.issubset({item["tconst"] for item in after_restart["items"]})
    patched = next(item for item in after_restart["items"] if item["tconst"] == second["tconst"])
    assert patched["priority"] == "P3"
    assert patched["status"] == "approve"

    delete_response = requests.delete(f"{BASE_URL}/api/shortlist/{first['tconst']}", timeout=5)
    assert delete_response.status_code in {200, 204}
    final_payload = requests.get(f"{BASE_URL}/api/shortlist", timeout=5).json()
    assert extract_shortlist_stats(final_payload)["totalItems"] == initial_stats["totalItems"] + 1


def test_browser_workflow() -> None:
    title = sorted(DEFAULT_DATASET["titles"], key=lambda item: (-item["averageRating"], -item["numVotes"]))[0]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        search_box = first_visible(
            page.get_by_test_id("filter-query"),
            page.get_by_placeholder("Search by title"),
            page.get_by_role("textbox", name="Search"),
            page.locator("input[name='query']"),
            page.locator("input[type='search']"),
            page.locator("input[type='text']"),
        )
        search_box.fill(title["primaryTitle"])
        first_visible(
            page.get_by_test_id("apply-filters"),
            page.get_by_role("button", name="应用筛选"),
            page.get_by_role("button", name="Apply Filters"),
            page.get_by_role("button", name="Apply"),
            page.locator("button[type='submit']"),
        ).click()
        with suppress(Exception):
            first_visible(
                page.get_by_test_id(f"title-card-{title['tconst']}"),
                page.get_by_role("link", name=title["primaryTitle"]),
            )
        with suppress(Exception):
            first_visible(
                page.get_by_test_id(f"open-detail-{title['tconst']}"),
                page.get_by_role("link", name=title["primaryTitle"]),
            ).click()
        if f"/titles/{title['tconst']}" not in page.url:
            page.goto(f"{BASE_URL}/titles/{title['tconst']}", wait_until="networkidle")
        detail_title = first_visible(
            page.get_by_test_id("detail-title"),
            page.get_by_role("heading", name=title["primaryTitle"]),
            page.get_by_text(title["primaryTitle"], exact=True),
        )
        maybe_fill_shortlist_note(page)
        first_visible(
            page.get_by_test_id(f"add-shortlist-{title['tconst']}"),
            page.get_by_role("button", name="Add to shortlist"),
            page.get_by_role("button", name="Save shortlist entry"),
            page.locator("button[type='submit']"),
        ).click()
        first_visible(
            page.get_by_test_id(f"shortlist-item-{title['tconst']}"),
            page.get_by_text(title["primaryTitle"], exact=True),
        )
        assert detail_title.inner_text() == title["primaryTitle"]
        status_grid_text = first_visible(
            page.get_by_test_id("shortlist-status-grid"),
            page.locator("body"),
        ).inner_text()
        assert "watch" in status_grid_text or "review" in status_grid_text
        browser.close()


def test_alternate_fixture_generalization() -> None:
    extra_titles = [title for title in ALT_DATASET["titles"] if title["tconst"] not in DEFAULT_DATASET["titleMap"]]
    assert extra_titles, "alternate fixture should contain at least one title absent from default snapshot"
    extra_title = extra_titles[0]
    RUNTIME.start(ALT_DATA_ROOT, reset_state=True, install=False, build=False, log_name="alt-start.log")

    response = requests.get(
        f"{BASE_URL}/api/titles",
        params={"query": extra_title["primaryTitle"], "sort": "rating_desc", "page": 1, "pageSize": 12},
        timeout=5,
    )
    payload = response.json()
    assert response.status_code == 200
    assert any(item["tconst"] == extra_title["tconst"] for item in payload["items"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        with suppress(Exception):
            search_box = first_visible(
                page.get_by_test_id("filter-query"),
                page.get_by_placeholder("Search by title"),
                page.get_by_role("textbox", name="Search"),
                page.locator("input[name='query']"),
                page.locator("input[type='search']"),
                page.locator("input[type='text']"),
            )
            search_box.fill(extra_title["primaryTitle"])
            first_visible(
                page.get_by_test_id("apply-filters"),
                page.get_by_role("button", name="应用筛选"),
                page.get_by_role("button", name="Apply Filters"),
                page.get_by_role("button", name="Apply"),
                page.locator("button[type='submit']"),
            ).click()
        if extra_title["primaryTitle"] not in page.content():
            page.goto(f"{BASE_URL}?query={quote(extra_title['primaryTitle'])}", wait_until="networkidle")
        first_visible(
            page.get_by_test_id(f"title-card-{extra_title['tconst']}"),
            page.get_by_role("link", name=extra_title["primaryTitle"]),
            page.get_by_text(extra_title["primaryTitle"], exact=True),
        )
        browser.close()

    RUNTIME.start(DATA_ROOT, reset_state=True, install=False, build=False, log_name="default-after-alt.log")


def test_input_integrity() -> None:
    expected_hashes = STATIC_HASH_PATH.read_text(encoding="utf-8").strip().splitlines()
    actual_hashes = []
    for file_path in sorted(DATA_ROOT.glob("*")):
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        actual_hashes.append(f"{digest}  {file_path}")
    assert len(expected_hashes) == len(actual_hashes)
    assert [line.split("  ")[0] for line in expected_hashes] == [line.split("  ")[0] for line in actual_hashes]


TESTS = [
    test_bootstrap_and_health,
    test_nextjs_app_router_scaffold,
    test_catalog_query_contract,
    test_detail_contract,
    test_shortlist_api_persistence,
    test_browser_workflow,
    test_alternate_fixture_generalization,
    test_input_integrity,
]


def main() -> int:
    results = []
    for test_fn in TESTS:
        nodeid = test_fn.__name__
        try:
            test_fn()
            results.append({"nodeid": nodeid, "outcome": "passed"})
            print(f"PASS {nodeid}")
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "nodeid": nodeid,
                    "outcome": "failed",
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            print(f"FAIL {nodeid}: {exc}")
            traceback.print_exc()
    RUNTIME.stop()
    report = {
        "tests": results,
        "summary": {
            "passed": sum(item["outcome"] == "passed" for item in results),
            "total": len(results),
        },
    }
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    (LOG_ROOT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (LOG_ROOT / "ctrf.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if all(item["outcome"] == "passed" for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
