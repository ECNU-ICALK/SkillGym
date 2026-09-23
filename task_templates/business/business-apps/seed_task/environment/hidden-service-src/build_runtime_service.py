from __future__ import annotations

import json
import pprint
import py_compile
from pathlib import Path


SRC_ROOT = Path("/opt/revops-task-env/hidden-service-src")
RUNTIME_ROOT = Path("/services/revops")


def main() -> None:
    server_src = SRC_ROOT / "server.py"
    state = json.loads((SRC_ROOT / "live_state.json").read_text(encoding="utf-8"))
    text = server_src.read_text(encoding="utf-8")
    needle = (
        'STATE_PATH = Path(os.environ.get("REVOPS_STATE_PATH", "/services/revops/live_state.json"))\n'
        'LOG_PATH = Path(os.environ.get("REVOPS_ACCESS_LOG", "/var/log/revops/access.log"))\n'
        "\n"
        'STATE = json.loads(STATE_PATH.read_text(encoding="utf-8"))\n'
    )
    replacement = (
        'LOG_PATH = Path(os.environ.get("REVOPS_ACCESS_LOG", "/var/log/revops/access.log"))\n'
        "\n"
        f"STATE = {pprint.pformat(state, sort_dicts=True)}\n"
    )
    text = text.replace(needle, replacement)
    runtime_py = RUNTIME_ROOT / "server_runtime.py"
    runtime_pyc = RUNTIME_ROOT / "server_runtime.pyc"
    runtime_py.write_text(text, encoding="utf-8")
    py_compile.compile(str(runtime_py), cfile=str(runtime_pyc), doraise=True)
    runtime_py.unlink()


if __name__ == "__main__":
    main()
