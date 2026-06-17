from __future__ import annotations

import shutil
import traceback

from playwright.sync_api import sync_playwright

from test_helpers import API, BASE, CONTRACT, DATA_ROOT, RELEASE_NOTES, build_alternate_fixture, ensure, fetch_json, restart_api


def test_api_contract() -> None:
  payload = fetch_json(f"{API}/api/bootstrap")
  ensure(payload["system"]["name"] == "Citi Bike", "Bootstrap returned the wrong system name")
  ensure(payload["contract"]["install_entry_name"] == CONTRACT["install_entry_name"], "Install entry name mismatch")
  ensure(len(payload["favorites"]["stations"]) == 6, "Favorite station count mismatch")
  ensure([item["label"] for item in payload["search_examples"]] == ["Broadway", "Central Park", "Allen"], "Search examples mismatch")
  ensure(payload["search_examples"][0]["expected_station_id"] == CONTRACT["offline_detail_station_id"], "Search example contract mismatch")


def test_mobile_flow_and_release_notes() -> None:
  ensure(RELEASE_NOTES.exists(), "release-notes.md was not written")
  release_notes = RELEASE_NOTES.read_text(encoding="utf-8")
  headings = CONTRACT["required_release_note_headings"]
  positions = [release_notes.find(heading) for heading in headings]
  ensure(all(position >= 0 for position in positions), "release-notes headings are incomplete")
  ensure(positions == sorted(positions), "release-notes heading order is incorrect")
  ensure(CONTRACT["install_entry_name"] in release_notes, "release-notes should mention the install entry name")

  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(viewport=CONTRACT["mobile_viewport"], is_mobile=True, has_touch=True)
    page = context.new_page()
    try:
      page.goto(BASE, wait_until="networkidle")
      page.locator("[data-testid='home-page']").wait_for()
      ensure((page.locator("[data-testid='favorite-count']").text_content() or "").strip() == "6", "Home page favorite count is wrong")
      page.locator("[data-testid='search-input']").fill("Allen")
      page.locator("[data-testid='results-list']").wait_for()
      ensure(page.locator("text=Allen St & Hester St").count() >= 1, "Search did not surface Allen St & Hester St")

      page.locator("[data-testid='favorites-grid']").locator(
        f"[data-testid='station-card-{CONTRACT['offline_detail_station_id']}']"
      ).click()
      page.locator("[data-testid='station-detail']").wait_for()
      page.locator("[data-testid='detail-name']").wait_for(timeout=20_000)
      ensure(page.locator("[data-testid='detail-name']").text_content() == CONTRACT["offline_detail_station_name"], "Detail route opened the wrong station")
      ensure(page.locator("[data-testid='detail-bikes']").text_content() is not None, "Detail bikes metric missing")
      ensure(page.locator("[data-testid='detail-docks']").text_content() is not None, "Detail docks metric missing")
      ensure(page.locator("[data-testid='detail-capacity']").text_content() is not None, "Detail capacity metric missing")

      page.goto(f"{BASE}/?entry=quick-access", wait_until="networkidle")
      page.locator("[data-testid='quick-access-banner']").wait_for()
      ensure(CONTRACT["install_entry_name"] in (page.locator("[data-testid='quick-access-banner']").text_content() or ""), "Quick-access banner did not use the install entry name")
    finally:
      context.close()
      browser.close()


def test_manifest_and_service_worker() -> None:
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(viewport=CONTRACT["mobile_viewport"])
    page = context.new_page()
    try:
      page.goto(BASE, wait_until="networkidle")
      manifest_href = page.evaluate(
        """
        () => {
          const node = document.querySelector('link[rel="manifest"]');
          return node ? node.getAttribute('href') : null;
        }
        """
      )
      ensure(manifest_href, "Manifest link is missing from the document head")
      manifest = fetch_json(f"{BASE}{manifest_href}")
      ensure(manifest["name"] == CONTRACT["install_entry_name"], "Manifest app name mismatch")
      ensure(manifest["start_url"] == CONTRACT["quick_access_start_url"], "Manifest start_url mismatch")
      ensure(manifest["display"] == "standalone", "Manifest display should be standalone")
      ensure(len(manifest["icons"]) >= 2, "Manifest icons are incomplete")

      page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.ready", timeout=10_000)
      page.reload(wait_until="networkidle")
      controller = page.evaluate("() => Boolean(navigator.serviceWorker && navigator.serviceWorker.controller)")
      ensure(controller, "Service worker did not take control after reload")
    finally:
      context.close()
      browser.close()


def test_online_refresh_beats_stale_copy() -> None:
  alt_dir, expected = build_alternate_fixture()
  alt_process = None
  try:
    with sync_playwright() as playwright:
      browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
      context = browser.new_context(viewport=CONTRACT["mobile_viewport"])
      page = context.new_page()
      try:
        page.goto(BASE, wait_until="networkidle")
        favorites = page.locator("[data-testid='favorites-grid']")
        favorites.locator(f"[data-testid='station-card-{CONTRACT['online_refresh_station_id']}']").wait_for()
        before = favorites.locator(f"[data-testid='bikes-{CONTRACT['online_refresh_station_id']}']").text_content()
        alt_process = restart_api(alt_dir)
        page.reload(wait_until="networkidle")
        favorites = page.locator("[data-testid='favorites-grid']")
        after = favorites.locator(f"[data-testid='bikes-{CONTRACT['online_refresh_station_id']}']").text_content()
        ensure(before != after, "Updated API snapshot did not change the favorite bikes count")
        ensure(after == str(expected["num_bikes_available"]), "Updated API value did not reach the UI")
        ensure(page.locator("[data-testid='source-state']").get_attribute("data-source-state") == "current", "Online refresh should stay on the current feed")
      finally:
        context.close()
        browser.close()
  finally:
    if alt_process:
      alt_process.terminate()
    restart_api(DATA_ROOT)
    shutil.rmtree(alt_dir.parent, ignore_errors=True)


def test_offline_reentry_uses_saved_content() -> None:
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(viewport=CONTRACT["mobile_viewport"], is_mobile=True, has_touch=True)
    page = context.new_page()
    try:
      page.goto(BASE, wait_until="networkidle")
      page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.ready", timeout=10_000)
      page.locator("[data-testid='favorites-grid']").locator(
        f"[data-testid='station-card-{CONTRACT['offline_detail_station_id']}']"
      ).click()
      page.locator("[data-testid='detail-name']").wait_for(timeout=20_000)
      online_source = page.locator("[data-testid='detail-source-state']").get_attribute("data-source-state")
      ensure(online_source in {"current", "saved"}, "Detail view should expose its freshness source")
      context.set_offline(True)
      page.reload(wait_until="domcontentloaded")
      page.locator("[data-testid='station-detail']").wait_for(timeout=10_000)
      ensure(
        page.locator("[data-testid='detail-source-state']").get_attribute("data-source-state") in {"current", "saved"},
        "Offline detail reload should keep a visible freshness source",
      )
      ensure(page.locator("[data-testid='detail-name']").text_content() == CONTRACT["offline_detail_station_name"], "Offline detail reload lost the retained station")

      page.goto(BASE, wait_until="domcontentloaded")
      page.locator("[data-testid='home-page']").wait_for(timeout=10_000)
      ensure(
        page.locator("[data-testid='source-state']").get_attribute("data-source-state") in {"current", "saved"},
        "Offline home re-entry should keep a visible freshness source",
      )
      ensure(
        page.locator("[data-testid='saved-banner']").count() >= 1 or page.locator("[data-testid='connectivity-banner']").count() >= 1,
        "Offline home re-entry should communicate that the user is working from a retained or disconnected state",
      )
      ensure(page.locator(f"text={CONTRACT['offline_detail_station_name']}").count() >= 1, "Offline home re-entry lost the retained station list")
    finally:
      context.close()
      browser.close()


def test_offline_fallback_page() -> None:
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(viewport=CONTRACT["mobile_viewport"], is_mobile=True, has_touch=True)
    page = context.new_page()
    try:
      page.goto(BASE, wait_until="networkidle")
      page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.ready", timeout=10_000)
      page.reload(wait_until="networkidle")
      context.set_offline(True)
      page.goto(f"{BASE}/offline.html", wait_until="domcontentloaded")
      title = (page.title() or "").lower()
      body_text = (page.locator("body").text_content() or "").lower()
      ensure("offline" in title, "Offline fallback page title should communicate offline status")
      ensure("offline" in body_text, "Offline fallback page body should communicate offline status")
      ensure(
        any(token in body_text for token in ["reconnect", "refresh", "return", "home"]),
        "Offline fallback page should give the user a recovery hint",
      )
    finally:
      context.close()
      browser.close()


def run_test(name: str, func, failures: list[str]) -> None:
  try:
    func()
    print(f"PASS: {name}")
  except Exception as error:
    print(f"FAIL: {name}")
    traceback.print_exception(error)
    failures.append(name)


def main() -> int:
  failures: list[str] = []
  tests = [
    ("api_contract", test_api_contract),
    ("mobile_flow_and_release_notes", test_mobile_flow_and_release_notes),
    ("manifest_and_service_worker", test_manifest_and_service_worker),
    ("online_refresh_beats_stale_copy", test_online_refresh_beats_stale_copy),
    ("offline_reentry_uses_saved_content", test_offline_reentry_uses_saved_content),
    ("offline_fallback_page", test_offline_fallback_page),
  ]
  for name, func in tests:
    run_test(name, func, failures)
  if failures:
    print(f"FAILED TESTS: {', '.join(failures)}")
    return 1
  print("All output checks passed.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
