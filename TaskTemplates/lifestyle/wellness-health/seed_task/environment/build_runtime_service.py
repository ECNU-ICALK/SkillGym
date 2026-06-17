from __future__ import annotations

import json
import py_compile
from pathlib import Path


SOURCE_PATH = Path("/services/wellness-planner/server.py")
SEED_PATH = Path("/opt/wellness-planner/seed/conditions_hourly.json")
RUNTIME_DIR = Path("/opt/wellness-runtime")
RUNTIME_PY = RUNTIME_DIR / "server_runtime.py"
RUNTIME_PYC = RUNTIME_DIR / "server_runtime.pyc"

MARKER = 'CONDITIONS = load_json(SEED_DIR / "conditions_hourly.json")\nBY_DATE = {row["date_local"]: row["hours"] for row in CONDITIONS["days"]}\n'


def main() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    conditions = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    replacement = (
        f"CONDITIONS = {conditions!r}\n"
        'BY_DATE = {row["date_local"]: row["hours"] for row in CONDITIONS["days"]}\n'
    )
    if MARKER not in source:
        raise RuntimeError("Unable to locate conditions loader marker in service source")

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_PY.write_text(source.replace(MARKER, replacement), encoding="utf-8")
    py_compile.compile(str(RUNTIME_PY), cfile=str(RUNTIME_PYC))
    RUNTIME_PY.unlink()


if __name__ == "__main__":
    main()
