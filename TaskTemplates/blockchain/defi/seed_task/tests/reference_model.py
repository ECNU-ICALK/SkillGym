from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExpectedModel:
    scenario_step_ids: list[str]
    scenario_actions: list[str]
    initial_fee_bps: int
    final_fee_bps: int
    total_reward_funding: int
    reward_duration_seconds: int
    governance_cap: str
    governance_quorum_votes: int
    governance_threshold: int
    governance_decimals: int


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_reference_model(spec_root: Path) -> ExpectedModel:
    launch_plan = _load_yaml(spec_root / "launch_plan.yaml")
    replay = _load_json(spec_root / "scenario_replay.json")
    rewards = _load_csv_rows(spec_root / "reward_program.csv")
    token_catalog = _load_json(spec_root / "token_catalog.json")

    step_ids = [item["step_id"] for item in replay["steps"]]
    actions = [item["action"] for item in replay["steps"]]
    total_reward_funding = sum(int(item["funding_amount"]) for item in rewards)

    return ExpectedModel(
        scenario_step_ids=step_ids,
        scenario_actions=actions,
        initial_fee_bps=int(launch_plan["pair"]["fee_bps"]),
        final_fee_bps=int(launch_plan["pair"]["fee_bps_after_governance"]),
        total_reward_funding=total_reward_funding,
        reward_duration_seconds=int(launch_plan["rewards"]["duration_seconds"]),
        governance_cap=str(launch_plan["governance_token"]["cap"]),
        governance_quorum_votes=int(launch_plan["governance"]["quorum_votes"]),
        governance_threshold=int(launch_plan["governance"]["proposal_threshold"]),
        governance_decimals=int(token_catalog["governance"]["decimals"]),
    )
