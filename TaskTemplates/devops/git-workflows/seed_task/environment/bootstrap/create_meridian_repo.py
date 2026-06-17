from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path


APP_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))
REPO_ROOT = Path(os.environ.get("TASK_REPO_ROOT", "/app/repo"))
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
BASELINE_ROOT = Path(os.environ.get("TASK_BASELINE_ROOT", "/opt/task-baselines"))


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def build_base_files(repo: Path) -> None:
    write(
        repo / "README.md",
        """
        # Meridian Checkout

        Internal checkout service for order total calculation and release hotfix packaging.
        """,
    )
    write(
        repo / ".gitignore",
        """
        .pytest_cache/
        __pycache__/
        artifacts/
        .worktrees/
        """,
    )
    write(
        repo / "pytest.ini",
        """
        [pytest]
        pythonpath = src
        """,
    )
    write(
        repo / "CLAUDE.md",
        """
        # Repo Notes

        Historical note: older release automation sometimes used `~/.config/superpowers/worktrees/meridian-hotfix`.

        If this repository already contains local worktree directories, keep using the existing repository convention instead of introducing a new worktree location.
        """,
    )
    (repo / ".worktrees").mkdir(parents=True, exist_ok=True)
    write(
        repo / "worktrees/README.md",
        """
        Legacy scratch area for temporary release workspaces.
        """,
    )
    write(
        repo / "src/meridian_checkout/__init__.py",
        """
        from .pricing import calculate_checkout_total
        """,
    )
    write(
        repo / "src/meridian_checkout/pricing.py",
        """
        from __future__ import annotations

        from decimal import Decimal, ROUND_HALF_UP


        def _round_cents(value: Decimal) -> int:
            return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


        def calculate_checkout_total(
            subtotal_cents: int,
            discount_cents: int,
            tax_rate_bps: int,
            shipping_cents: int = 0,
        ) -> dict[str, int]:
            discounted_subtotal_cents = max(subtotal_cents - discount_cents, 0)
            taxable_cents = discounted_subtotal_cents
            tax_cents = _round_cents(Decimal(taxable_cents) * Decimal(tax_rate_bps) / Decimal(10000))
            total_cents = discounted_subtotal_cents + shipping_cents + tax_cents
            return {
                "subtotal_cents": subtotal_cents,
                "discount_cents": discount_cents,
                "tax_cents": tax_cents,
                "shipping_cents": shipping_cents,
                "total_cents": total_cents,
            }
        """,
    )
    write(
        repo / "tests/test_pricing.py",
        """
        from meridian_checkout.pricing import calculate_checkout_total


        def test_discount_is_applied_before_tax() -> None:
            result = calculate_checkout_total(
                subtotal_cents=10000,
                discount_cents=2500,
                tax_rate_bps=875,
                shipping_cents=500,
            )
            assert result["tax_cents"] == 656
            assert result["total_cents"] == 8656


        def test_discount_is_capped_at_zero() -> None:
            result = calculate_checkout_total(
                subtotal_cents=900,
                discount_cents=1500,
                tax_rate_bps=725,
            )
            assert result["tax_cents"] == 0
            assert result["total_cents"] == 0
        """,
    )
    write(
        repo / "scripts/build_release_notes.py",
        """
        from __future__ import annotations

        import json
        import os
        import sys
        from collections import defaultdict
        from pathlib import Path


        SECTION_ORDER = ["Fixes", "Risks", "Validation"]


        def load_request(path: Path) -> dict:
            return json.loads(path.read_text(encoding="utf-8"))


        def load_fragments(path: Path) -> list[dict]:
            rows = []
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
            return rows


        def main() -> None:
            if len(sys.argv) != 3:
                raise SystemExit("usage: build_release_notes.py <fragments.ndjson> <output.md>")

            data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
            request_path = data_root / "hotfix_request.json"
            request = load_request(request_path)
            fragments = load_fragments(Path(sys.argv[1]))
            grouped: dict[str, list[str]] = defaultdict(list)
            for fragment in fragments:
                if fragment["release_version"] != request["release_version"]:
                    continue
                if not fragment.get("include", True):
                    continue
                grouped[fragment["section"]].append(fragment["text"])

            lines = [
                f"# {request['notes_title']}",
                "",
                f"Base branch: `{request['release_branch']}`",
                f"Target branch: `{request['hotfix_branch']}`",
                "",
            ]
            for section in SECTION_ORDER:
                entries = grouped.get(section, [])
                if not entries:
                    continue
                lines.append(f"## {section}")
                for entry in entries:
                    lines.append(f"- {entry}")
                lines.append("")

            Path(sys.argv[2]).write_text("\\n".join(lines).rstrip() + "\\n", encoding="utf-8")


        if __name__ == "__main__":
            main()
        """,
    )
    write(
        repo / "scripts/write_hotfix_report.py",
        """
        from __future__ import annotations

        import json
        import os
        import subprocess
        import sys
        from pathlib import Path


        def git(*args: str) -> str:
            result = subprocess.run(
                ["git", *args],
                text=True,
                capture_output=True,
                check=True,
            )
            return result.stdout.strip()


        def main() -> None:
            if len(sys.argv) != 2:
                raise SystemExit("usage: write_hotfix_report.py <output.json>")

            data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
            request = json.loads((data_root / "hotfix_request.json").read_text(encoding="utf-8"))
            output_path = Path(sys.argv[1])
            report = {
                "service": request["service"],
                "release_version": request["release_version"],
                "release_branch": request["release_branch"],
                "hotfix_branch": request["hotfix_branch"],
                "current_branch": git("branch", "--show-current"),
                "git_head": git("rev-parse", "HEAD"),
                "worktree_path": str(Path.cwd()),
                "release_notes_path": str((Path.cwd() / "artifacts" / "release_notes.md").resolve()),
                "smoke_checks_passed": True,
            }
            output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


        if __name__ == "__main__":
            main()
        """,
    )
    run_hotfix_path = repo / "ops/hotfix/run_hotfix.sh"
    write(
        run_hotfix_path,
        """
        #!/usr/bin/env bash
        set -euo pipefail

        DATA_ROOT="${TASK_DATA_ROOT:-/root/data}"
        REQUEST_JSON="$DATA_ROOT/hotfix_request.json"
        REPO_ROOT="$(git rev-parse --show-toplevel)"
        ARTIFACT_DIR="$REPO_ROOT/artifacts"

        release_branch="$(python3 - <<'PY'
        import os
        import json
        from pathlib import Path
        data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
        request = json.loads((data_root / "hotfix_request.json").read_text(encoding="utf-8"))
        print(request["release_branch"])
        PY
        )"
        hotfix_branch="$(python3 - <<'PY'
        import os
        import json
        from pathlib import Path
        data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
        request = json.loads((data_root / "hotfix_request.json").read_text(encoding="utf-8"))
        print(request["hotfix_branch"])
        PY
        )"

        current_branch="$(git branch --show-current)"
        if [ "$current_branch" != "$hotfix_branch" ]; then
          echo "expected branch $hotfix_branch, got $current_branch" >&2
          exit 1
        fi

        git merge-base --is-ancestor "$release_branch" HEAD

        export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
        mkdir -p "$ARTIFACT_DIR"

        pytest -q tests/test_pricing.py

        python3 - <<'PY'
        from meridian_checkout.pricing import calculate_checkout_total

        smoke_cases = [
            (10000, 2500, 875, 500, 8656),
            (900, 1500, 725, 0, 0),
            (4200, 0, 825, 300, 4847),
        ]
        for subtotal, discount, tax_bps, shipping, expected_total in smoke_cases:
            result = calculate_checkout_total(subtotal, discount, tax_bps, shipping)
            assert result["total_cents"] == expected_total, (subtotal, discount, tax_bps, shipping, result)
        PY

        python3 scripts/build_release_notes.py "$DATA_ROOT/changelog_fragments.ndjson" "$ARTIFACT_DIR/release_notes.md"
        python3 scripts/write_hotfix_report.py "$ARTIFACT_DIR/hotfix_report.json"
        """,
    )
    run_hotfix_path.chmod(0o755)
    write(
        repo / "audit/investigation.md",
        """
        # Checkout Audit Notes

        Pending checkout audit notes. Keep this working copy intact while preparing the hotfix.
        """,
    )


def build_release_branch_files(repo: Path) -> None:
    write(
        repo / "src/meridian_checkout/pricing.py",
        """
        from __future__ import annotations

        from decimal import Decimal, ROUND_HALF_UP


        def _round_cents(value: Decimal) -> int:
            return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


        def calculate_checkout_total(
            subtotal_cents: int,
            discount_cents: int,
            tax_rate_bps: int,
            shipping_cents: int = 0,
        ) -> dict[str, int]:
            discounted_subtotal_cents = max(subtotal_cents - discount_cents, 0)
            taxable_cents = subtotal_cents
            tax_cents = _round_cents(Decimal(taxable_cents) * Decimal(tax_rate_bps) / Decimal(10000))
            total_cents = discounted_subtotal_cents + shipping_cents + tax_cents
            return {
                "subtotal_cents": subtotal_cents,
                "discount_cents": discount_cents,
                "tax_cents": tax_cents,
                "shipping_cents": shipping_cents,
                "total_cents": total_cents,
            }
        """,
    )


def build_main_branch_files(repo: Path) -> None:
    write(
        repo / "src/meridian_checkout/pricing.py",
        """
        from __future__ import annotations

        from decimal import Decimal, ROUND_HALF_UP


        def _round_cents(value: Decimal) -> int:
            return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


        def calculate_checkout_total(
            subtotal_cents: int,
            discount_cents: int,
            tax_rate_bps: int,
            shipping_cents: int = 0,
            trace: dict | None = None,
        ) -> dict[str, int]:
            discounted_subtotal_cents = max(subtotal_cents - discount_cents, 0)
            taxable_cents = max(subtotal_cents, 0)
            tax_cents = _round_cents(Decimal(taxable_cents) * Decimal(tax_rate_bps) / Decimal(10000))
            total_cents = discounted_subtotal_cents + shipping_cents + tax_cents
            if trace is not None:
                trace["pricing_path"] = "audit-preview"
                trace["discount_applied"] = discounted_subtotal_cents
            return {
                "subtotal_cents": subtotal_cents,
                "discount_cents": discount_cents,
                "tax_cents": tax_cents,
                "shipping_cents": shipping_cents,
                "total_cents": total_cents,
            }
        """,
    )
    write(
        repo / "audit/investigation.md",
        """
        # Checkout Audit Notes

        Pending checkout audit notes. Keep this working copy intact while preparing the hotfix.

        Mainline audit scaffolding is still under review.
        """,
    )


def apply_dirty_state(repo: Path) -> None:
    pricing_path = repo / "src/meridian_checkout/pricing.py"
    text = pricing_path.read_text(encoding="utf-8")
    marker = '        trace["discount_applied"] = discounted_subtotal_cents\n'
    replacement = marker + '        trace["reviewer"] = "checkout-audit"\n'
    pricing_path.write_text(text.replace(marker, replacement), encoding="utf-8")

    investigation_path = repo / "audit/investigation.md"
    investigation_path.write_text(
        investigation_path.read_text(encoding="utf-8").rstrip()
        + "\n- Keep the current working copy unchanged until audit sign-off.\n",
        encoding="utf-8",
    )


def snapshot_primary_state(repo: Path) -> None:
    BASELINE_ROOT.mkdir(parents=True, exist_ok=True)
    (BASELINE_ROOT / "root_branch.txt").write_text(
        run(["git", "branch", "--show-current"], cwd=repo) + "\n",
        encoding="utf-8",
    )
    (BASELINE_ROOT / "root_status.txt").write_text(
        run(["git", "status", "--short"], cwd=repo) + "\n",
        encoding="utf-8",
    )
    (BASELINE_ROOT / "root_diff.patch").write_text(
        run(["git", "diff", "--", "src/meridian_checkout/pricing.py", "audit/investigation.md"], cwd=repo) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if REPO_ROOT.exists():
        shutil.rmtree(REPO_ROOT)
    REPO_ROOT.mkdir(parents=True, exist_ok=True)

    run(["git", "init", "-b", "main"], cwd=REPO_ROOT)
    run(["git", "config", "user.name", "Meridian Release Bot"], cwd=REPO_ROOT)
    run(["git", "config", "user.email", "release-bot@example.com"], cwd=REPO_ROOT)

    build_base_files(REPO_ROOT)
    run(["git", "add", "."], cwd=REPO_ROOT)
    run(["git", "commit", "-m", "feat(checkout): add checkout pricing baseline"], cwd=REPO_ROOT)

    run(["git", "checkout", "-b", "release/2026.04"], cwd=REPO_ROOT)
    build_release_branch_files(REPO_ROOT)
    run(["git", "add", "src/meridian_checkout/pricing.py"], cwd=REPO_ROOT)
    run(["git", "commit", "-m", "fix(checkout): regress discount tax order on release branch"], cwd=REPO_ROOT)

    run(["git", "checkout", "main"], cwd=REPO_ROOT)
    build_main_branch_files(REPO_ROOT)
    run(["git", "add", "src/meridian_checkout/pricing.py", "audit/investigation.md"], cwd=REPO_ROOT)
    run(["git", "commit", "-m", "feat(audit): add mainline pricing trace scaffolding"], cwd=REPO_ROOT)

    apply_dirty_state(REPO_ROOT)
    snapshot_primary_state(REPO_ROOT)

    metadata = {
        "repo_root": str(REPO_ROOT),
        "release_branch": "release/2026.04",
        "primary_branch": "main",
        "target_hotfix_branch": "hotfix-2026.04.3",
        "preferred_worktree_root": str(REPO_ROOT / ".worktrees"),
    }
    (BASELINE_ROOT / "repo_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
