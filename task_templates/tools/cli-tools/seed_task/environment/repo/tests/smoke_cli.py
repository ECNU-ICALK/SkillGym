from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "tests" / "fixtures" / "ourairports"
CONTRACT = ROOT / "tests" / "fixtures" / "contracts" / "release_contract.json"
BUILD_ROOT = ROOT / "build"


def ensure_release_prereqs() -> None:
    pydeps = BUILD_ROOT / "pydeps"
    pydeps.mkdir(parents=True, exist_ok=True)
    (pydeps / ".ready").write_text("", encoding="utf-8")


def _run_source(*args: str) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "airdesk", "--data-dir", str(DATA_DIR), *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def _run_packaged(executable: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(executable), "--data-dir", str(DATA_DIR), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def main() -> int:
    ensure_release_prereqs()
    with tempfile.TemporaryDirectory() as tmpdir:
        release_dir = Path(tmpdir) / "release"
        proc = _run_source(
            "release",
            "--contract",
            str(CONTRACT),
            "--output-dir",
            str(release_dir),
            "--format",
            "json",
        )
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr)
            return 1

        smoke_expected = json.loads((release_dir / "smoke_expected.json").read_text(encoding="utf-8"))
        package_dir = "airdesk_0.4.0_linux_amd64"
        artifact_name = f"{package_dir}.tar.gz"
        with tarfile.open(release_dir / artifact_name, "r:gz") as archive:
            archive.extractall(Path(tmpdir) / "unpacked")
        executable = Path(tmpdir) / "unpacked" / package_dir / "bin" / "airdesk"

        for case in smoke_expected.values():
            args = case["args"]
            if args == ["--help"]:
                run = _run_packaged(executable, "--help")
            else:
                run = _run_packaged(executable, *args)
            if run.returncode != 0:
                print(run.stdout)
                print(run.stderr)
                return 1
            if run.stdout != case["stdout"]:
                print("stdout mismatch")
                print("expected:")
                print(case["stdout"])
                print("actual:")
                print(run.stdout)
                return 1
    print("cli smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
