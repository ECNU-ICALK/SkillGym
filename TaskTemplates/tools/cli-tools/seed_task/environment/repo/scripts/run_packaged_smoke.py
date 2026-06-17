from __future__ import annotations

import argparse
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()

    release_dir = Path(args.release_dir)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    smoke_expected = json.loads((release_dir / "smoke_expected.json").read_text(encoding="utf-8"))
    artifact_path = release_dir / str(contract["artifact_name"])
    package_dir = f"{contract['package_name']}_{contract['version']}_linux_amd64"

    with tempfile.TemporaryDirectory() as tmpdir:
        unpack_root = Path(tmpdir) / "unpacked"
        with tarfile.open(artifact_path, "r:gz") as archive:
            archive.extractall(unpack_root)

        executable = unpack_root / package_dir / "bin" / "airdesk"
        if not executable.exists():
            raise SystemExit(f"missing packaged executable: {executable}")

        for case in contract["smoke_cases"]:
            case_id = case["id"]
            cmd = [str(executable)]
            if case["args"] != ["--help"]:
                cmd.extend(["--data-dir", args.data_dir])
            cmd.extend(case["args"])
            proc = run(cmd)
            if proc.returncode != 0:
                raise SystemExit(f"{case_id}: returncode={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
            if proc.stdout != smoke_expected[case_id]["stdout"]:
                raise SystemExit(f"{case_id}: stdout mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
