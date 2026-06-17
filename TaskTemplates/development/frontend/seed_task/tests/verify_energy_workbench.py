from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE = "http://localhost:3000"
API = "http://localhost:3001"
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
SERVICE_ROOT = Path(os.environ.get("API_ROOT", "/services/energy-api"))
APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
AGENT_LOG = Path(os.environ.get("AGENT_LOG", "/logs/agent/codex.txt"))
VERIFIER_LOG_ROOT = Path(os.environ.get("VERIFIER_LOG_ROOT", "/logs/verifier"))

EXPECTED_FILE_HASHES = {
    DATA_ROOT / "owid_energy_snapshot.csv": "9523f224812334e12864632b48eb6c04afacbb7c24ba926ba080fec96d8e809e",
    DATA_ROOT / "owid_energy_codebook.csv": "5bbe57339ca2f838af5535acc4caff7697dc5e4ac49b3b9e7247fd8ad681a9d7",
    DATA_ROOT / "world_bank_countries.json": "dd0829c09b5f68e350a058b87f65604e96e93ee465182afdabb3442209cbcf8c",
    SERVICE_ROOT / "server.js": "5573aa23b8ba2fe28b11f02734dfad6951e2d413bd5718669008cc3f95dcb943",
}


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_codes(page) -> list[str]:
    rows = page.locator('[data-testid="country-table-body"] tr')
    return [
        rows.nth(index).get_attribute("data-country-code")
        for index in range(rows.count())
    ]


def close_drawer(page) -> None:
    drawer = page.locator('[data-testid="country-drawer"]')
    drawer.wait_for()
    page.locator('[data-testid="drawer-close"]').wait_for()
    drawer.get_by_role("button", name="Close").click()


def focus_details_trigger(page, iso_code: str):
    trigger = page.locator(f'[data-testid="open-details-{iso_code}"]').first
    trigger.wait_for()
    trigger.focus()
    return trigger


def compare_codes(page) -> list[str]:
    chips = page.locator('[data-testid="compare-chip-row"] [data-country-code]')
    return [chips.nth(index).get_attribute("data-country-code") for index in range(chips.count())]


def mix_codes(page) -> list[str]:
    rows = page.locator('[data-testid="mix-list"] .mix-row')
    return [rows.nth(index).get_attribute("data-country-code") for index in range(rows.count())]


def assert_overview_mode(page, expected: str) -> None:
    ensure(expected in {"table", "renewables"}, f"Unexpected overview mode assertion: {expected}")
    active_testid = page.evaluate(
        """
        () => {
          const active = document.querySelector('[data-testid="overview-mode-toggle"] [aria-pressed="true"]');
          return active ? active.getAttribute('data-testid') : null;
        }
        """
    )
    ensure(
        active_testid == f"overview-mode-{expected}",
        f"Overview mode drifted, expected {expected} but got {active_testid}",
    )


def assert_region_stable(page, expected: str, *, duration_ms: int = 1200, interval_ms: int = 120) -> None:
    seen = []
    deadline = time.monotonic() + (duration_ms / 1000)
    while True:
      current = (page.locator('[data-testid="active-region-label"]').text_content() or "").strip()
      seen.append(current)
      ensure(current == expected, f"Active region drifted: {' -> '.join(seen)}")
      if time.monotonic() >= deadline:
          break
      page.wait_for_timeout(interval_ms)


def wait_for_region(page, expected: str, *, timeout_ms: int = 2000) -> None:
    page.wait_for_function(
        """
        (target) => {
          const node = document.querySelector('[data-testid="active-region-label"]');
          return node && node.textContent.trim() === target;
        }
        """,
        arg=expected,
        timeout=timeout_ms,
    )


def assert_drawer_country_stable(page, expected_name: str, expected_code: str, *, duration_ms: int = 500) -> None:
    seen = []
    deadline = time.monotonic() + (duration_ms / 1000)
    while True:
        title = (page.locator('[data-testid="drawer-title"]').text_content() or "").strip()
        code = (page.locator('[data-testid="detail-iso-code"]').text_content() or "").strip()
        seen.append(f"{title}/{code}")
        ensure(title == expected_name, f"Drawer title drifted: {' -> '.join(seen)}")
        ensure(code == expected_code, f"Drawer ISO drifted: {' -> '.join(seen)}")
        if time.monotonic() >= deadline:
            break
        page.wait_for_timeout(100)


def install_runtime_probe(page) -> None:
    page.add_init_script(
        """
        (() => {
          const stats = { added: 0, removed: 0, active: 0 };
          const counts = new WeakMap();
          const add = EventTarget.prototype.addEventListener;
          const remove = EventTarget.prototype.removeEventListener;

          EventTarget.prototype.addEventListener = function(type, listener, options) {
            if ((this === window || this === document) && type === 'keydown' && typeof listener === 'function') {
              const current = counts.get(listener) || 0;
              counts.set(listener, current + 1);
              stats.added += 1;
              stats.active += 1;
            }
            return add.call(this, type, listener, options);
          };

          EventTarget.prototype.removeEventListener = function(type, listener, options) {
            if ((this === window || this === document) && type === 'keydown' && typeof listener === 'function') {
              const current = counts.get(listener) || 0;
              if (current > 0) {
                if (current === 1) {
                  counts.delete(listener);
                } else {
                  counts.set(listener, current - 1);
                }
                stats.removed += 1;
                stats.active -= 1;
              }
            }
            return remove.call(this, type, listener, options);
          };

          window.__listenerStats = stats;
        })();
        """
    )


def collect_js_urls(page):
    urls = []

    def handle_response(response):
        if response.status != 200:
            return
        content_type = response.headers.get("content-type", "")
        if ".js" not in response.url and "javascript" not in content_type:
            return
        urls.append(response.url)

    page.on("response", handle_response)
    return urls


def wait_for_health(base_url: str, *, attempts: int = 30) -> None:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=10) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError(f"Service at {base_url} did not become healthy")


def restart_alt_api(data_dir: Path):
    subprocess.run(["fuser", "-k", "3001/tcp"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = os.environ.copy()
    env["ENERGY_DATA_DIR"] = str(data_dir)
    process = subprocess.Popen(
        ["npm", "start"],
        cwd=SERVICE_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_health(API)
    return process


def build_alternate_fixture() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="energy-alt-fixture."))
    shutil.copytree(DATA_ROOT, temp_root / "data")

    snapshot_path = temp_root / "data" / "owid_energy_snapshot.csv"
    with snapshot_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "Spain,ESP,2022,47828318,1887848364300,248.270,287.150,2.737,29.984,4.071,6.126,12.439,21.863,20.404\n"
        )
        handle.write(
            "Spain,ESP,2023,48373336,,251.320,279.110,1.297,23.059,3.755,8.957,17.409,23.030,20.375\n"
        )

    countries_path = temp_root / "data" / "world_bank_countries.json"
    countries = json.loads(countries_path.read_text(encoding="utf-8"))
    countries.append(
        {
            "id": "ESP",
            "iso2Code": "ES",
            "name": "Spain",
            "region": "Europe & Central Asia",
            "incomeLevel": "High income",
            "lendingType": "Not classified",
        }
    )
    countries_path.write_text(json.dumps(countries, indent=2), encoding="utf-8")
    return temp_root / "data"


def test_api_uses_real_snapshot() -> None:
    start = time.monotonic()
    with urllib.request.urlopen(f"{API}/api/dashboard", timeout=30) as response:
        payload = json.load(response)
    elapsed = (time.monotonic() - start) * 1000

    ensure(elapsed >= 100, f"/api/dashboard returned too quickly ({elapsed:.0f}ms)")
    ensure(payload["snapshotId"] == "owid-energy-workbench-2023-snapshot", "Unexpected snapshotId")
    ensure(len(payload["countries"]) == 10, "Expected 10 country rows in the base snapshot")
    germany = next(item for item in payload["countries"] if item["isoCode"] == "DEU")
    ensure(germany["region"] == "Europe & Central Asia", "Germany region mismatch")
    ensure(round(germany["renewablesShare"], 3) == 44.532, "Germany renewables share mismatch")
    with urllib.request.urlopen(f"{API}/api/countries/DEU", timeout=30) as response:
        details = json.load(response)
    ensure(details["isoCode"] == "DEU", "Detail endpoint returned the wrong country")
    ensure(details["dominantRenewableSource"] == "Wind", "Unexpected dominant renewable source for Germany")


def test_deeplink_state_survives_reload_and_history() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        try:
            page.add_init_script(
                """
                localStorage.setItem(
                  'energy-workbench-state',
                  JSON.stringify({
                    region: 'North America',
                    compareCodes: ['USA', 'CAN'],
                    updatedAt: Date.now() - 1000
                  })
                );
                """
            )
            deeplink = (
                f"{BASE}/?region=Europe%20%26%20Central%20Asia"
                "&search=fr&sort=generation-desc&compare=FRA,DEU&compareView=open&drawer=FRA"
            )
            page.goto(deeplink, wait_until="networkidle")
            assert_region_stable(page, "Europe & Central Asia")
            ensure(table_codes(page) == ["FRA"], f"Unexpected table ordering: {table_codes(page)}")
            ensure(compare_codes(page) == ["FRA", "DEU"], f"Unexpected compare chips: {compare_codes(page)}")
            ensure(page.locator('[data-testid="compare-workspace"]').count() == 1, "Compare workspace did not restore")
            ensure(
                (page.locator('[data-testid="stat-visible-count"]').text_content() or "").strip() == "1",
                "Visible count card drifted away from the filtered table",
            )
            ensure(
                (page.locator('[data-testid="stat-top-country"]').text_content() or "").strip() == "France",
                "Top country card did not follow the filtered table",
            )
            ensure(mix_codes(page)[:1] == ["FRA"], f"Mix highlight drifted away from the filtered table: {mix_codes(page)}")

            page.reload(wait_until="networkidle")
            assert_region_stable(page, "Europe & Central Asia", duration_ms=900)
            ensure(table_codes(page) == ["FRA"], "Search-filtered table changed after reload")
            ensure(compare_codes(page) == ["FRA", "DEU"], "Compare selection changed after reload")
            ensure(page.locator('[data-testid="compare-workspace"]').count() == 1, "Compare workspace closed after reload")
            ensure(mix_codes(page)[:1] == ["FRA"], "Mix highlight changed after reload")

            if page.locator('[data-testid="country-drawer"]').count():
                close_drawer(page)

            before_history = page.evaluate("history.length")
            page.locator('[data-testid="compare-toggle"]').click()
            page.locator('[data-testid="compare-workspace"]').wait_for(state="hidden")
            after_compare_history = page.evaluate("history.length")
            ensure(
                after_compare_history >= before_history + 1,
                "Compare workspace toggle did not create a browser history entry",
            )

            page.reload(wait_until="networkidle")
            ensure(compare_codes(page) == ["FRA", "DEU"], "Compare chips changed after compare workspace reload")
            ensure(page.locator('[data-testid="compare-workspace"]').count() == 0, "Compare workspace reopened after reload")

            page.evaluate("history.back()")
            page.locator('[data-testid="compare-workspace"]').wait_for()
            ensure(compare_codes(page) == ["FRA", "DEU"], "Back navigation lost compare selection")
            ensure(table_codes(page) == ["FRA"], "Back navigation did not restore the France-only table")
            ensure(mix_codes(page)[:1] == ["FRA"], "Back navigation did not restore mix highlight")

            page.locator('[data-testid="search-input"]').fill("")
            page.locator('[data-testid="region-select"]').select_option("North America")
            wait_for_region(page, "North America")
            ensure(table_codes(page)[:2] == ["USA", "CAN"], f"North America ordering mismatch: {table_codes(page)}")
            ensure(
                (page.locator('[data-testid="stat-visible-count"]').text_content() or "").strip() == "2",
                "Visible count card did not update for North America",
            )
            ensure(
                (page.locator('[data-testid="stat-top-country"]').text_content() or "").strip() == "United States",
                "Top country card did not follow North America sorting",
            )
            ensure(mix_codes(page)[:2] == ["USA", "CAN"], f"Mix highlight did not follow North America sorting: {mix_codes(page)}")

            page.evaluate("history.back()")
            wait_for_region(page, "Europe & Central Asia")
            assert_region_stable(page, "Europe & Central Asia")
            ensure(page.locator('[data-testid="compare-workspace"]').count() == 1, "Back navigation did not restore compare view")
            ensure(compare_codes(page) == ["FRA", "DEU"], "Back navigation did not restore compare selection")
        finally:
            context.close()
            browser.close()


def test_country_drawer_chunk_loads_on_demand_and_latest_intent_wins() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        try:
            js_urls = collect_js_urls(page)
            detail_urls = []

            def handle_response(response):
                if response.status == 200 and "/api/countries/" in response.url:
                    detail_urls.append(response.url)

            page.on("response", handle_response)
            page.goto(f"{BASE}/?region=Europe%20%26%20Central%20Asia&sort=renewables-desc", wait_until="networkidle")
            ensure(
                not any("country-drawer" in url for url in js_urls),
                f"Country drawer chunk loaded before user intent: {js_urls}",
            )

            page.locator('[data-testid="open-details-DEU"]').click()
            page.locator('[data-testid="detail-iso-code"]').wait_for()
            ensure(
                any("country-drawer" in url for url in js_urls),
                f"Country drawer chunk never loaded on demand: {js_urls}",
            )
            ensure(
                any("/api/countries/DEU" in url for url in detail_urls),
                f"Country drawer never requested DEU detail data: {detail_urls}",
            )
            close_drawer(page)
            page.locator('[data-testid="country-drawer"]').wait_for(state="hidden")

            page.evaluate(
                """
                () => {
                  document.querySelector('[data-testid="open-details-DEU"]').click();
                  setTimeout(() => {
                    document.querySelector('[data-testid="open-details-FRA"]').click();
                  }, 30);
                }
                """
            )
            page.locator('[data-testid="detail-iso-code"]').wait_for()
            page.wait_for_timeout(700)
            ensure("drawer=FRA" in page.url, f"URL did not keep the latest drawer target: {page.url}")
            assert_drawer_country_stable(page, "France", "FRA")

            close_drawer(page)
            page.locator('[data-testid="country-drawer"]').wait_for(state="hidden")

            page.evaluate(
                """
                () => {
                  document.querySelector('[data-testid="open-details-FRA"]').click();
                  setTimeout(() => {
                    document.querySelector('[data-testid="open-details-DEU"]').click();
                  }, 30);
                }
                """
            )
            page.locator('[data-testid="detail-iso-code"]').wait_for()
            page.wait_for_timeout(800)
            ensure("drawer=DEU" in page.url, f"URL did not keep the second latest drawer target: {page.url}")
            assert_drawer_country_stable(page, "Germany", "DEU")
        finally:
            context.close()
            browser.close()


def test_overview_mode_survives_reload_history_and_share() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        try:
            deeplink = f"{BASE}/?region=Europe%20%26%20Central%20Asia&sort=generation-desc&overview=renewables"
            page.goto(deeplink, wait_until="networkidle")
            assert_region_stable(page, "Europe & Central Asia")
            assert_overview_mode(page, "renewables")
            ensure(table_codes(page)[:3] == ["FRA", "DEU", "GBR"], f"Unexpected table ordering: {table_codes(page)}")
            ensure(
                mix_codes(page)[:3] == ["DEU", "GBR", "FRA"],
                f"Renewables overview ordering drifted: {mix_codes(page)}",
            )
            ensure("overview=renewables" in page.url, f"Share URL lost overview context: {page.url}")

            page.reload(wait_until="networkidle")
            assert_region_stable(page, "Europe & Central Asia", duration_ms=900)
            assert_overview_mode(page, "renewables")
            ensure(
                mix_codes(page)[:3] == ["DEU", "GBR", "FRA"],
                f"Renewables overview changed after reload: {mix_codes(page)}",
            )

            before_history = page.evaluate("history.length")
            page.locator('[data-testid="overview-mode-table"]').click()
            assert_overview_mode(page, "table")
            ensure(
                mix_codes(page)[:3] == ["FRA", "DEU", "GBR"],
                f"Table overview ordering drifted: {mix_codes(page)}",
            )
            ensure("overview=renewables" not in page.url, f"Table mode URL kept stale overview context: {page.url}")
            after_history = page.evaluate("history.length")
            ensure(after_history >= before_history + 1, "Overview mode change did not create a history entry")

            page.reload(wait_until="networkidle")
            assert_overview_mode(page, "table")
            ensure(
                mix_codes(page)[:3] == ["FRA", "DEU", "GBR"],
                f"Table overview changed after reload: {mix_codes(page)}",
            )

            page.evaluate("history.back()")
            page.wait_for_function(
                """
                () => {
                  const active = document.querySelector('[data-testid="overview-mode-toggle"] [aria-pressed="true"]');
                  return active && active.getAttribute('data-testid') === 'overview-mode-renewables';
                }
                """
            )
            assert_overview_mode(page, "renewables")
            ensure(
                mix_codes(page)[:3] == ["DEU", "GBR", "FRA"],
                f"Back navigation did not restore renewables overview: {mix_codes(page)}",
            )
            ensure("overview=renewables" in page.url, f"Back navigation lost overview context in URL: {page.url}")
        finally:
            context.close()
            browser.close()


def test_drawer_modal_behavior_and_cleans_up_listeners() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        install_runtime_probe(page)
        try:
            page.goto(f"{BASE}/?region=Europe%20%26%20Central%20Asia&sort=renewables-desc", wait_until="networkidle")
            baseline = page.evaluate("({ ...window.__listenerStats })")
            for _ in range(3):
                focus_details_trigger(page, "DEU")
                page.keyboard.press("Enter")
                page.locator('[data-testid="drawer-close"]').wait_for()
                active_testid = page.evaluate(
                    "document.activeElement ? document.activeElement.getAttribute('data-testid') : null"
                )
                ensure(active_testid == "drawer-close", f"Drawer did not focus its close control, got {active_testid}")
                page.keyboard.press("Tab")
                active_testid = page.evaluate(
                    "document.activeElement ? document.activeElement.getAttribute('data-testid') : null"
                )
                ensure(active_testid == "drawer-close", f"Drawer did not trap focus, got {active_testid}")
                page.locator(".drawer-backdrop").click(force=True)
                page.locator('[data-testid="country-drawer"]').wait_for(state="hidden")

            stats = page.evaluate("window.__listenerStats")
            ensure(
                stats["active"] <= baseline["active"] + 1,
                f"Active listeners kept growing after drawer cycles: baseline={baseline}, final={stats}",
            )
            ensure(
                (stats["added"] - stats["removed"]) <= (baseline["added"] - baseline["removed"]) + 1,
                f"Listener cleanup mismatch: baseline={baseline}, final={stats}",
            )
        finally:
            context.close()
            browser.close()


def test_behavior_generalizes_on_alternate_fixture() -> None:
    alt_data = build_alternate_fixture()
    alt_process = None
    try:
        alt_process = restart_alt_api(alt_data)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            try:
                page.goto(
                    f"{BASE}/?region=Europe%20%26%20Central%20Asia&sort=renewables-desc",
                    wait_until="networkidle",
                )
                ensure(table_codes(page)[0] == "ESP", f"Alternate fixture did not surface Spain first: {table_codes(page)}")
            finally:
                context.close()
                browser.close()
    finally:
        if alt_process is not None:
            alt_process.terminate()
            alt_process.wait(timeout=15)


def test_static_inputs_and_hidden_service_unchanged() -> None:
    for path, expected_hash in EXPECTED_FILE_HASHES.items():
        ensure(path.exists(), f"Protected input missing: {path}")
        ensure(sha256_path(path) == expected_hash, f"Protected input changed: {path}")


def test_skill_was_available_if_present() -> None:
    skill_md = Path("/logs/agent/skills/frontend-patterns/SKILL.md")
    if not skill_md.exists() or not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    ensure(
        "/logs/agent/skills/frontend-patterns/SKILL.md" in text
        or "/root/.codex/skills/frontend-patterns/SKILL.md" in text,
        "Agent log did not show access to the bound skill",
    )


def main() -> int:
    tests = [
        test_api_uses_real_snapshot,
        test_deeplink_state_survives_reload_and_history,
        test_country_drawer_chunk_loads_on_demand_and_latest_intent_wins,
        test_overview_mode_survives_reload_history_and_share,
        test_drawer_modal_behavior_and_cleans_up_listeners,
        test_behavior_generalizes_on_alternate_fixture,
        test_static_inputs_and_hidden_service_unchanged,
        test_skill_was_available_if_present,
    ]
    results = []

    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            results.append({"name": fn.__name__, "outcome": "passed"})
        except Exception as exc:
            print(f"FAIL {fn.__name__}: {exc}")
            traceback.print_exc()
            results.append(
                {
                    "name": fn.__name__,
                    "outcome": "failed",
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    log_root = VERIFIER_LOG_ROOT
    log_root.mkdir(parents=True, exist_ok=True)
    report = {
        "tests": results,
        "summary": {
            "passed": sum(result["outcome"] == "passed" for result in results),
            "total": len(results),
        },
    }
    (log_root / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if all(result["outcome"] == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
