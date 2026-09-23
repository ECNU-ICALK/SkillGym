from __future__ import annotations

import json
from pathlib import Path

import yaml

from common import (
    REPORT_PATH,
    SPEC_HASH_PATH,
    SPEC_ROOT,
    load_report,
    run_hardhat_script,
    run_replay,
    run_replay_in_temp,
    run_replay_in_temp_with_spec_overrides,
    sha256sum_style_listing,
)
from reference_model import build_reference_model


def _load_probe_json(script_path: Path, workspace_root: Path | None = None) -> dict:
    output = run_hardhat_script(script_path, workspace_root=workspace_root or SPEC_ROOT.parent)
    start = output.find("{")
    end = output.rfind("}")
    assert start != -1 and end != -1 and end >= start, f"Probe did not emit JSON.\nOutput:\n{output}"
    return json.loads(output[start : end + 1])


def _as_int(value):
    return int(value) if isinstance(value, str) else value


def _proposal_status(report: dict) -> dict | None:
    for key in ("proposal_status", "active_proposal", "proposal", "latest_proposal"):
        proposal = report["governance_token"].get(key)
        if proposal is not None:
            return proposal
    if report.get("scenario_results"):
        governance = report["scenario_results"][-1].get("governance", {})
        for key in ("proposal_status", "active_proposal", "proposal", "latest_proposal"):
            proposal = governance.get(key)
            if proposal is not None:
                return proposal
    return None


def _current_votes(report: dict) -> dict:
    votes = {}
    current_votes = report["governance_token"].get("current_votes")
    if isinstance(current_votes, dict):
        votes.update(current_votes)
    actor_summaries = report.get("actor_summaries", {})
    votes.update(
        {
            actor: summary.get("delegated_voting_power", summary.get("voting_power", summary.get("votes")))
            for actor, summary in actor_summaries.items()
            if "delegated_voting_power" in summary or "voting_power" in summary or "votes" in summary
        }
    )
    if report.get("scenario_results"):
        latest_actor_state = report["scenario_results"][-1].get("actors", {})
        votes.update(
            {
                actor: summary.get("delegated_voting_power", summary.get("voting_power", summary.get("votes")))
                for actor, summary in latest_actor_state.items()
                if "delegated_voting_power" in summary or "voting_power" in summary or "votes" in summary
            }
        )
    return votes


def _lp_balances(report: dict) -> dict:
    balances = report["pair"].get("lp_balances")
    if balances is not None:
        return balances
    actor_summaries = report.get("actor_summaries", {})
    return {
        actor: summary["lp_balance"]
        for actor, summary in actor_summaries.items()
        if "lp_balance" in summary
    }


def _staker_balances(report: dict) -> dict:
    balances = report["reward_program"].get("staker_balances")
    if balances is not None:
        return balances
    actor_summaries = report.get("actor_summaries", {})
    return {
        actor: summary.get("staked_lp_balance", summary.get("staked_lp"))
        for actor, summary in actor_summaries.items()
        if "staked_lp_balance" in summary or "staked_lp" in summary
    }


def test_spec_hashes_not_modified() -> None:
    if SPEC_HASH_PATH.exists():
        expected_spec_hashes = SPEC_HASH_PATH.read_text(encoding="utf-8")
        actual_spec_hashes = sha256sum_style_listing(SPEC_ROOT)
        assert actual_spec_hashes == expected_spec_hashes, "Input spec files were modified"


def test_report_is_regenerated_from_execution() -> None:
    result, workspace_copy = run_replay_in_temp()
    assert result.returncode == 0, (
        "Fresh replay run failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    report_path = workspace_copy / "out" / "launch_report.json"
    fresh = load_report(report_path)

    report_path.write_text('{"tampered": true}\n', encoding="utf-8")
    rerun = run_replay(workspace_root=workspace_copy)
    assert rerun.returncode == 0, (
        "Replay rerun failed after tamper.\n"
        f"stdout:\n{rerun.stdout}\n"
        f"stderr:\n{rerun.stderr}"
    )

    regenerated = load_report(report_path)
    assert "tampered" not in regenerated, "Replay entrypoint did not overwrite tampered report"
    assert {"pair", "governance_token", "reward_program", "scenario_results", "invariant_checks"}.issubset(
        regenerated.keys()
    ), "Replay output missing required sections after rerun"
    assert regenerated["pair"] == fresh["pair"], "Pair state changed unexpectedly across immediate rerun"


def test_action_level_constraints_hold() -> None:
    model = build_reference_model(SPEC_ROOT)
    report = load_report()

    # Governance path must drive parameter change, not static formatting output.
    assert _as_int(report["pair"]["fee_bps"]) == model.final_fee_bps
    assert _as_int(report["pair"]["fee_bps"]) != model.initial_fee_bps

    proposal = _proposal_status(report)
    assert proposal["executed"] is True
    assert proposal["queued"] is True
    for_votes = int(proposal.get("for_votes", proposal.get("forVotes")))
    against_votes = int(proposal.get("against_votes", proposal.get("againstVotes")))
    assert for_votes >= model.governance_quorum_votes
    assert for_votes > against_votes

    # Rewards accounting must remain bounded and produce non-zero claims.
    total_funded = int(report["reward_program"]["total_funded"])
    total_claimed = int(report["reward_program"]["total_claimed"])
    assert total_funded == model.total_reward_funding
    assert 0 < total_claimed <= total_funded


def test_governance_token_decimals_follow_mutated_catalog() -> None:
    catalog = json.loads((SPEC_ROOT / "token_catalog.json").read_text(encoding="utf-8"))
    catalog["governance"]["decimals"] = 6
    catalog["governance"]["name"] = "Launch Governance Token Six"
    catalog["governance"]["symbol"] = "GOV6"

    result, workspace_copy = run_replay_in_temp_with_spec_overrides(
        {"token_catalog.json": json.dumps(catalog, indent=2) + "\n"}
    )
    assert result.returncode == 0, (
        "Mutated replay run failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    report = load_report(workspace_copy / "out" / "launch_report.json")
    assert report["governance_token"]["name"] == "Launch Governance Token Six"
    assert report["governance_token"]["symbol"] == "GOV6"
    assert _as_int(report["governance_token"]["decimals"]) == 6

    probe = _load_probe_json(Path(__file__).resolve().parent / "probe_governance_decimals.js", workspace_copy)
    assert probe["name"] == "Launch Governance Token Six"
    assert probe["symbol"] == "GOV6"
    assert probe["decimals"] == 6


def test_pair_component_behaviors_hold_under_direct_probe() -> None:
    probe = _load_probe_json(Path(__file__).resolve().parent / "probe_pair_behaviors.js")

    assert probe["removed_amount0"] == "100000000000000000000"
    assert probe["removed_amount1"] == "50000000000000000000"
    assert probe["reserves_after_remove0"] == "400000000000000000000"
    assert probe["reserves_after_remove1"] == "200000000000000000000"
    assert probe["actual_swap_out"] == probe["expected_swap_out"]
    assert int(probe["k_after_swap"]) >= int(probe["k_before_swap"])


def test_pair_reserves_resync_to_actual_balances_after_external_transfers() -> None:
    probe = _load_probe_json(Path(__file__).resolve().parent / "probe_pair_reserve_sync.js")

    assert probe["reserve0"] == probe["actual_balance0"]
    assert probe["reserve1"] == probe["actual_balance1"]


def test_staking_rollover_accounting_holds_under_direct_probe() -> None:
    probe = _load_probe_json(Path(__file__).resolve().parent / "probe_staking_rollover.js")

    assert probe["actual_second_rate"] == probe["expected_second_rate"]
    assert int(probe["earned_alice_before_claim"]) > 0
    assert int(probe["alice_reward_balance"]) > 0
    assert 0 < int(probe["total_claimed"]) <= int(probe["total_funded"])
    assert probe["remaining_bob_stake"] == "0"


def test_replay_generalizes_to_extra_actor_and_dynamic_summaries() -> None:
    launch_plan = yaml.safe_load((SPEC_ROOT / "launch_plan.yaml").read_text(encoding="utf-8"))
    replay = json.loads((SPEC_ROOT / "scenario_replay.json").read_text(encoding="utf-8"))

    launch_plan["governance_token"]["cap"] = str(
        int(launch_plan["governance_token"]["cap"]) + 30_000_000_000_000_000_000_000
    )
    launch_plan["governance_token"]["initial_allocations"]["dave"] = "30000000000000000000000"
    launch_plan["assets"]["base"]["initial_allocations"]["dave"] = "50000000000000000000000"
    launch_plan["assets"]["quote"]["initial_allocations"]["dave"] = "25000000000000000000000"

    replay["steps"].extend(
        [
            {
                "step_id": "STEP-028",
                "action": "add_liquidity",
                "actor": "dave",
                "amount0": "20000000000000000000000",
                "amount1": "10000000000000000000000",
            },
            {
                "step_id": "STEP-029",
                "action": "stake_lp",
                "actor": "dave",
                "share_bps": 5000,
            },
            {
                "step_id": "STEP-030",
                "action": "delegate_votes",
                "actor": "dave",
                "delegatee": "dave",
            },
        ]
    )

    result, workspace_copy = run_replay_in_temp_with_spec_overrides(
        {
            "launch_plan.yaml": yaml.safe_dump(launch_plan, sort_keys=False),
            "scenario_replay.json": json.dumps(replay, indent=2) + "\n",
        }
    )
    assert result.returncode == 0, (
        "Mutated replay with an extra actor failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    report = load_report(workspace_copy / "out" / "launch_report.json")
    assert "dave" in _lp_balances(report)
    assert "dave" in _staker_balances(report)
    assert "dave" in _current_votes(report)
    observed_actions = [item["action"] for item in report["scenario_results"]]
    assert {"add_liquidity", "stake_lp", "delegate_votes"}.issubset(observed_actions)
