from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


CAMPAIGN_ROOT = Path(os.environ.get("TASK_CAMPAIGN_ROOT", "/app/campaign"))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", "/app/workspace"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/app/output"))
BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_content_pack.py"
CONTRACT_PATH = CAMPAIGN_ROOT / "brief" / "channel_contract.json"
CLAIM_BANK_PATH = CAMPAIGN_ROOT / "data" / "claim_bank.json"
SOURCE_MANIFEST_PATH = CAMPAIGN_ROOT / "data" / "source_manifest.json"
BASELINE_SHA256_PATH = Path(os.environ.get("TASK_BASELINE_SHA256_PATH", "/opt/task-baselines/campaign.sha256"))
BANNED_PHRASES = load_json = None


def run_build(campaign_root: Path = CAMPAIGN_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--campaign-root",
            str(campaign_root),
            "--output-root",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def campaign_integrity_listing(root: Path = CAMPAIGN_ROOT) -> str:
    lines: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path}")
    return "\n".join(lines) + "\n"


def claims_by_id(root: Path = CAMPAIGN_ROOT) -> dict[str, dict]:
    return {claim["id"]: claim for claim in load_json(root / "data" / "claim_bank.json")["claims"]}


def parse_thread_posts(text: str) -> list[str]:
    blocks = [block.strip() for block in text.strip().split("\n\n") if block.strip()]
    return blocks


def parse_video_scenes(text: str) -> list[str]:
    scenes = [chunk.strip() for chunk in text.strip().split("\n\n") if chunk.strip()]
    return scenes


def shingle_overlap(a: str, b: str, size: int = 3) -> float:
    def shingles(text: str) -> set[tuple[str, ...]]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if len(tokens) < size:
            return set()
        return {tuple(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}

    left = shingles(a)
    right = shingles(b)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def make_alternate_campaign_copy() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory()
    alt_root = Path(tmpdir.name) / "campaign"
    shutil.copytree(CAMPAIGN_ROOT, alt_root)

    contract = load_json(alt_root / "brief" / "channel_contract.json")
    contract["audience"] = "board-ready public summary for climate and infrastructure decision-makers"
    contract["campaign_title"] = "Renewable Capacity Momentum 2025: Gap Check"
    (alt_root / "brief" / "channel_contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    brief = read_text(alt_root / "brief" / "editorial_brief.md")
    brief = brief.replace(
        "climate-tech operators, policy teams, and business readers who need a concise public-facing summary",
        "board-ready public summary for climate and infrastructure decision-makers",
    )
    brief = brief.replace("Renewable Capacity Momentum 2025", "Renewable Capacity Momentum 2025: Gap Check")
    (alt_root / "brief" / "editorial_brief.md").write_text(brief, encoding="utf-8")

    claim_bank = load_json(alt_root / "data" / "claim_bank.json")
    for claim in claim_bank["claims"]:
        if claim["id"] == "C01":
            claim["statement"] = "Global renewable power capacity reached 4,520 GW in 2024 after a 612 GW annual increase."
            claim["data"]["capacity_gw"] = 4520
            claim["data"]["annual_addition_gw"] = 612
        if claim["id"] == "C04":
            claim["statement"] = "Current government ambitions still sit closer to 8,600 GW by 2030."
            claim["data"]["ambition_gw"] = 8600
        if claim["id"] == "C09":
            claim["statement"] = "The bundled China 2023 row reports 610 TWh of solar generation and 920 TWh of wind generation."
            claim["data"]["solar_twh"] = 610
            claim["data"]["wind_twh"] = 920
    (alt_root / "data" / "claim_bank.json").write_text(json.dumps(claim_bank, indent=2) + "\n", encoding="utf-8")

    return tmpdir, alt_root
