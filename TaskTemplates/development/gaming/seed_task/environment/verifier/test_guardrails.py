from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", str(APP_ROOT / "data")))
STUDIO_DIR = Path(os.environ.get("TASK_STUDIO_DIR", str(APP_ROOT / "workspace/studio")))
DATA_HASH_PATH = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/kanto-atlas-data.sha256"))


def test_inputs_were_not_modified() -> None:
    current = subprocess.check_output(
        f"find {DATA_DIR} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected = DATA_HASH_PATH.read_text(encoding="utf-8")
    assert current == expected, "input data under /app/data was modified"


def test_no_placeholder_or_verifier_hints_in_studio_files() -> None:
    for path in STUDIO_DIR.glob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        filtered = re.sub(r"\.placeholder\b", "", text)
        filtered = re.sub(r"\bplaceholder\s*=", "", filtered)
        assert "placeholder" not in filtered
        assert " todo " not in f" {text} "
        assert "verifier" not in text
        assert "/tests" not in text
