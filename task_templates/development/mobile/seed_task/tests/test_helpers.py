from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:3000"
API = "http://localhost:3001"
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
DATA_ROOT = Path(os.environ.get("DATA_ROOT", WORKSPACE_ROOT / "data"))
APP_ROOT = Path(os.environ.get("APP_ROOT", WORKSPACE_ROOT / "app"))
API_ROOT = Path(os.environ.get("API_ROOT", "/services/citibike-api"))
RELEASE_NOTES = WORKSPACE_ROOT / "artifacts" / "release-notes.md"
CONTRACT = json.loads((DATA_ROOT / "delivery_contract.json").read_text(encoding="utf-8"))


def ensure(condition: bool, message: str) -> None:
  if not condition:
    raise AssertionError(message)


def sha256_path(path: Path) -> str:
  return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_json(url: str) -> dict:
  with urllib.request.urlopen(url, timeout=30) as response:
    return json.load(response)


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


def restart_api(data_dir: Path):
  subprocess.run(["fuser", "-k", "3001/tcp"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  env = os.environ.copy()
  env["CITIBIKE_DATA_DIR"] = str(data_dir)
  env["CITIBIKE_API_PORT"] = "3001"
  process = subprocess.Popen(
    ["npm", "start"],
    cwd=API_ROOT,
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
  )
  wait_for_health(API)
  return process


def build_alternate_fixture() -> tuple[Path, dict[str, int]]:
  temp_root = Path(tempfile.mkdtemp(prefix="bikeboard-alt-fixture."))
  shutil.copytree(DATA_ROOT, temp_root / "data")
  fixture_dir = temp_root / "data"

  target_station_id = CONTRACT["online_refresh_station_id"]
  status_path = fixture_dir / "station_status.json"
  payload = json.loads(status_path.read_text(encoding="utf-8"))
  changes = {
    "num_bikes_available": 9,
    "num_docks_available": 17,
    "is_renting": 1,
    "is_returning": 1,
    "is_installed": 1,
    "last_reported": 1777743999,
  }
  for station in payload["data"]["stations"]:
    if station["station_id"] == target_station_id:
      station.update(changes)
  payload["last_updated"] = 1777744001
  status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

  return fixture_dir, changes
