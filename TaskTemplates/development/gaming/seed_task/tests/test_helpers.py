from __future__ import annotations

import hashlib
import http.server
import json
import math
import os
import re
import socketserver
import threading
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from playwright.sync_api import Page, sync_playwright


APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
STUDIO_DIR = Path(os.environ.get("TASK_STUDIO_DIR", "/app/workspace/studio"))
DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/app/data"))
HTTP_PORT = int(os.environ.get("TASK_HTTP_PORT", "8765"))
PAGE_URL = f"http://127.0.0.1:{HTTP_PORT}/workspace/studio/index.html"

_SERVER = None
_SERVER_THREAD = None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract() -> dict[str, Any]:
    return load_json(DATA_DIR / "render_contract.json")


def encounter_data() -> dict[str, Any]:
    return load_json(DATA_DIR / "encounter_zones.json")


def type_relations_data() -> dict[str, Any]:
    return load_json(DATA_DIR / "type_relations.json")


def species_data() -> dict[str, Any]:
    return load_json(DATA_DIR / "pokedex_kanto.json")


def expected_zone_metrics(zone_id: str) -> dict[str, Any]:
    zone = next(zone for zone in encounter_data()["zones"] if zone["zone_id"] == zone_id)
    encounters = zone["encounters"]
    species_count = len(encounters)
    avg_min = round(sum(row["min_level"] for row in encounters) / species_count, 1)
    avg_max = round(sum(row["max_level"] for row in encounters) / species_count, 1)
    avg_bst = round(sum(row["base_stat_total"] for row in encounters) / species_count, 1)
    type_counts: dict[str, int] = {}
    for row in encounters:
        for type_name in row["types"]:
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
    top_types = [name for name, _ in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[:3]]
    return {
        "zone": zone,
        "species_count": species_count,
        "avg_min": avg_min,
        "avg_max": avg_max,
        "avg_bst": avg_bst,
        "top_types": top_types,
        "encounter_species": {row["species_name"] for row in encounters},
    }


def expected_zone_pressure(zone_id: str) -> dict[str, Any]:
    metrics = expected_zone_metrics(zone_id)
    types_by_name = {row["type_name"]: row for row in type_relations_data()["types"]}
    coverage: set[str] = set()
    exposure: set[str] = set()
    for type_name in metrics["top_types"]:
        row = types_by_name.get(type_name, {})
        coverage.update(row.get("double_damage_to", []))
        exposure.update(row.get("double_damage_from", []))
    return {
        "top_types": metrics["top_types"],
        "coverage": coverage,
        "exposure": exposure,
    }


def start_server() -> None:
    global _SERVER, _SERVER_THREAD
    if _SERVER is not None:
        return

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(APP_ROOT), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            return

    _SERVER = socketserver.TCPServer(("127.0.0.1", HTTP_PORT), QuietHandler)
    _SERVER_THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True)
    _SERVER_THREAD.start()


@contextmanager
def page_session(viewport: dict[str, int] | None = None, url: str = PAGE_URL) -> Iterator[Page]:
    start_server()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=viewport or {"width": 1440, "height": 1120},
            accept_downloads=True,
        )
        page = context.new_page()
        seen_console: list[str] = []
        seen_requests: list[str] = []
        page.on("console", lambda msg: seen_console.append(f"{msg.type}: {msg.text}"))
        page.on("request", lambda req: seen_requests.append(req.url))
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_function("window.__ATLAS_READY__ === true", timeout=30000)
        page.wait_for_timeout(150)
        page._console_messages = seen_console  # type: ignore[attr-defined]
        page._request_urls = seen_requests  # type: ignore[attr-defined]
        try:
            yield page
        finally:
            context.close()
            browser.close()


def page_overview(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const metricText = (id) => {
            const node = document.getElementById(id);
            return node ? node.textContent.trim() : '';
          };
          const links = Array.from(document.querySelectorAll('#source-links a')).map((node) => ({
            href: node.getAttribute('href'),
            text: node.textContent.trim(),
          }));
          return {
            title: document.title,
            idsPresent: [
              'seed-display', 'seed-input', 'seed-prev', 'seed-next', 'seed-random', 'seed-go',
              'zone-select', 'preset-survey', 'preset-bloom', 'preset-storm',
              'density-control', 'turbulence-control', 'focus-control', 'contrast-control',
              'color1', 'color2', 'color3',
              'regenerate-button', 'reset-button', 'export-button', 'export-status', 'export-json',
              'route-title', 'route-summary', 'metric-species-count', 'metric-avg-level', 'metric-avg-bst',
              'metric-type-mix', 'highlighted-species', 'source-links', 'type-pressure', 'zone-signals'
            ].filter((id) => document.getElementById(id)),
            routeTitle: metricText('route-title'),
            routeSummary: metricText('route-summary'),
            metrics: {
              speciesCount: metricText('metric-species-count'),
              avgLevel: metricText('metric-avg-level'),
              avgBst: metricText('metric-avg-bst'),
              typeMix: metricText('metric-type-mix'),
            },
            highlighted: Array.from(document.querySelectorAll('#highlighted-species [data-species-id]')).map((node) => ({
              speciesId: node.getAttribute('data-species-id'),
              text: node.textContent.trim(),
            })),
            sourceLinks: links,
            exportStatus: metricText('export-status'),
            exportValue: (document.getElementById('export-json') || {}).value || '',
            canvasCount: document.querySelectorAll('canvas').length,
            remoteRefs: Array.from(document.querySelectorAll('script[src], link[href], img[src], iframe[src], source[src]'))
              .map((node) => node.getAttribute('src') || node.getAttribute('href') || '')
              .filter((value) => /^https?:\\/\\//i.test(value)),
            seedDisplay: metricText('seed-display'),
            seedInput: (document.getElementById('seed-input') || {}).value || '',
            zoneValue: (document.getElementById('zone-select') || {}).value || '',
            controls: {
              density: Number((document.getElementById('density-control') || {}).value || 0),
              turbulence: Number((document.getElementById('turbulence-control') || {}).value || 0),
              focus: Number((document.getElementById('focus-control') || {}).value || 0),
              contrast: Number((document.getElementById('contrast-control') || {}).value || 0),
            },
            colors: {
              color1: ((document.getElementById('color1') || {}).value || '').toLowerCase(),
              color2: ((document.getElementById('color2') || {}).value || '').toLowerCase(),
              color3: ((document.getElementById('color3') || {}).value || '').toLowerCase(),
            },
          };
        }
        """
    )


def console_messages(page: Page) -> list[str]:
    return list(getattr(page, "_console_messages", []))


def request_urls(page: Page) -> list[str]:
    return list(getattr(page, "_request_urls", []))


def hash_state(page: Page) -> dict[str, str]:
    state = page.evaluate(
        """
        () => Object.fromEntries(new URLSearchParams(window.location.hash.slice(1)).entries())
        """
    )
    for key in ("color1", "color2", "color3"):
        value = state.get(key)
        if value and not value.startswith("#") and re.fullmatch(r"[0-9a-fA-F]{6}", value):
            state[key] = f"#{value.lower()}"
    return state


def canvas_hash(page: Page) -> str:
    png = page.locator("canvas").first.screenshot()
    return hashlib.sha256(png).hexdigest()


def click_export(page: Page) -> dict[str, Any]:
    page.click("#export-button")
    page.wait_for_timeout(120)
    payload = page.locator("#export-json").evaluate(
        """
        (node) => {
          if ("value" in node && typeof node.value === "string") {
            return node.value;
          }
          return node.textContent || "";
        }
        """
    )
    return json.loads(payload)


def set_seed(page: Page, seed: int) -> None:
    page.fill("#seed-input", str(seed))
    page.click("#seed-go")
    page.wait_for_timeout(120)


def select_zone(page: Page, zone_id: str) -> None:
    page.select_option("#zone-select", zone_id)
    page.wait_for_timeout(120)


def click_preset(page: Page, preset_id: str) -> None:
    page.click(f"#preset-{preset_id}")
    page.wait_for_timeout(120)


def set_color(page: Page, color_id: str, value: str) -> None:
    page.evaluate(
        """
        ([id, nextValue]) => {
          const input = document.getElementById(id);
          input.value = nextValue;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        [color_id, value],
    )
    page.wait_for_timeout(120)


def set_slider(page: Page, slider_id: str, value: float) -> None:
    page.evaluate(
        """
        ([id, nextValue]) => {
          const input = document.getElementById(id);
          input.value = String(nextValue);
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        [slider_id, value],
    )
    page.wait_for_timeout(120)


def parse_float(text: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        raise AssertionError(f"expected numeric content in {text!r}")
    return float(match.group(0))


def sample_groups(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload["sample_points"]:
        groups[str(row["trail_id"])].append(row)
    for rows in groups.values():
        rows.sort(key=lambda item: int(item["step"]))
    return dict(groups)


def _angle_delta(a: float, b: float) -> float:
    diff = (b - a + math.pi) % (math.pi * 2) - math.pi
    return abs(diff)


def sample_stats(payload: dict[str, Any]) -> dict[str, float]:
    points = payload["sample_points"]
    xs = [float(row["x"]) for row in points]
    ys = [float(row["y"]) for row in points]
    centroid_x = sum(xs) / len(xs)
    centroid_y = sum(ys) / len(ys)
    groups = sample_groups(payload)
    distances = [
        math.hypot(float(row["x"]) - centroid_x, float(row["y"]) - centroid_y)
        for row in points
    ]
    turn_deltas: list[float] = []
    lengths: list[int] = []
    for rows in groups.values():
        lengths.append(len(rows))
        if len(rows) < 3:
            continue
        headings: list[float] = []
        for idx in range(1, len(rows)):
            prev = rows[idx - 1]
            cur = rows[idx]
            headings.append(
                math.atan2(float(cur["y"]) - float(prev["y"]), float(cur["x"]) - float(prev["x"]))
            )
        for idx in range(1, len(headings)):
            turn_deltas.append(_angle_delta(headings[idx - 1], headings[idx]))
    return {
        "point_count": float(len(points)),
        "trail_count": float(len(groups)),
        "min_trail_points": float(min(lengths) if lengths else 0),
        "mean_trail_points": float(sum(lengths) / len(lengths) if lengths else 0),
        "mean_distance": float(sum(distances) / len(distances)),
        "turn_dispersion": float(sum(turn_deltas) / len(turn_deltas) if turn_deltas else 0),
    }
