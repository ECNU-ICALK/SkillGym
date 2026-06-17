from __future__ import annotations

import traceback

from test_helpers import API_ROOT, APP_ROOT, CONTRACT, DATA_ROOT, ensure, sha256_path

EXPECTED_FILE_HASHES = {
  DATA_ROOT / "system_information.json": "46fb6acb0b9c13cd86cd9f6dd2476609206976b99d3a805ae12754d37d4bbe54",
  DATA_ROOT / "station_information.json": "07bce793ce446c3ac6a92a717a0563d26ac711f1645d451712473d3b26e3c606",
  DATA_ROOT / "station_status.json": "f6d9948bec523cccebd579c0b982b8ea3094061eab62c02b554df8b25a7a2304",
  DATA_ROOT / "favorite_stations.json": "38029f067aade6a386c3b827c090f6461d2bebcb68799f3402292d0c200bea61",
  DATA_ROOT / "search_queries.json": "eca031b97ca0bef0d22e02a19617152a9ce5b4281cdaf4f75fb6c1f69eb365f4",
  DATA_ROOT / "delivery_contract.json": "5114c999586d0efc298d03b7e271eab98db8c3871210f66abc419f234c6d8d31",
  API_ROOT / "server.js": "d3817e1b28d8ff3d95e7de470878528368f19aa03368b4ca9453ea0df4096d32",
}


def test_protected_inputs_unchanged() -> None:
  for path, expected_hash in EXPECTED_FILE_HASHES.items():
    ensure(path.exists(), f"Missing protected file: {path}")
    ensure(sha256_path(path) == expected_hash, f"Protected file changed: {path}")


def test_solver_kept_app_shape() -> None:
  ensure((APP_ROOT / "src" / "App.jsx").exists(), "App entry is missing")
  ensure((APP_ROOT / "src" / "main.jsx").exists(), "Main entry is missing")
  ensure((APP_ROOT / "src" / "api.js").exists(), "API client is missing")
  ensure(
    (APP_ROOT / "public" / "manifest.webmanifest").exists() or (APP_ROOT / "public" / "manifest.json").exists(),
    "Manifest file is missing",
  )
  ensure((APP_ROOT / "public" / "sw.js").exists(), "Service worker file is missing")
  ensure(CONTRACT["quick_access_start_url"] == "/?entry=quick-access", "Delivery contract quick-access route changed")


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
    ("protected_inputs_unchanged", test_protected_inputs_unchanged),
    ("solver_kept_app_shape", test_solver_kept_app_shape),
  ]
  for name, func in tests:
    run_test(name, func, failures)
  if failures:
    print(f"FAILED TESTS: {', '.join(failures)}")
    return 1
  print("All guardrail checks passed.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
