from __future__ import annotations

from pathlib import Path

from common import REPORT_PATH, SPEC_ROOT, load_report, run_query_state, run_replay_in_temp
from reference_model import build_reference_model


REQUIRED_TOP_LEVEL_KEYS = {
    "pair",
    "governance_token",
    "reward_program",
    "scenario_results",
    "invariant_checks",
}


def _normalize(value):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in {
                "period_finish",
                "eta",
                "block_number",
                "timestamp",
                "observed_offset_seconds",
                "lateness_seconds",
                "observed_value",
            }:
                continue
            out[key] = _normalize(item)
        return out
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


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


def _proposal_count(report: dict) -> int:
    if "proposal_count" in report["governance_token"]:
        return _as_int(report["governance_token"]["proposal_count"])
    proposal = _proposal_status(report)
    return 1 if proposal is not None else 0


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


def _stable_report_projection(report: dict) -> dict:
    proposal = _proposal_status(report)
    return {
        "pair": {
            "fee_bps": _as_int(report["pair"]["fee_bps"]),
            "reserve0": report["pair"]["reserve0"],
            "reserve1": report["pair"]["reserve1"],
            "total_lp_supply": report["pair"]["total_lp_supply"],
            "lp_balance_actors": sorted(_lp_balances(report).keys()),
        },
        "governance_token": {
            "name": report["governance_token"]["name"],
            "symbol": report["governance_token"]["symbol"],
            "decimals": _as_int(report["governance_token"]["decimals"]),
            "cap": report["governance_token"]["cap"],
            "proposal_count": _proposal_count(report),
            "current_vote_actors": sorted(_current_votes(report).keys()),
            "proposal_status": {
                "queued": proposal["queued"] if proposal else None,
                "executed": proposal["executed"] if proposal else None,
                "for_votes": proposal.get("for_votes", proposal.get("forVotes")) if proposal else None,
                "against_votes": proposal.get("against_votes", proposal.get("againstVotes")) if proposal else None,
            },
        },
        "reward_program": {
            "total_funded": report["reward_program"]["total_funded"],
            "rewards_duration_seconds": _as_int(report["reward_program"]["rewards_duration_seconds"]),
            "epoch_ids": [item["epoch_id"] for item in report["reward_program"].get("epochs", [])],
            "staker_actors": sorted(_staker_balances(report).keys()),
        },
        "scenario_results": [(item["step_id"], item["action"]) for item in report["scenario_results"]],
        "actor_summaries": sorted(report.get("actor_summaries", {}).keys()),
    }


def test_required_output_file_exists() -> None:
    assert REPORT_PATH.exists(), "Missing /root/workspace/out/launch_report.json"


def test_report_contract_and_basic_shape() -> None:
    report = load_report()
    assert REQUIRED_TOP_LEVEL_KEYS.issubset(report.keys()), "Report missing required top-level keys"

    assert isinstance(report["scenario_results"], list), "scenario_results must be an array"
    assert isinstance(report["invariant_checks"], list), "invariant_checks must be an array"
    for item in report["invariant_checks"]:
        assert isinstance(item, dict), "Each invariant check entry must be an object"
        assert {"name", "status", "observed_value"}.issubset(item.keys())

    assert isinstance(report["pair"]["reserve0"], str)
    assert isinstance(report["pair"]["reserve1"], str)
    assert isinstance(report["reward_program"]["total_funded"], str)
    assert isinstance(report["reward_program"]["total_claimed"], str)


def test_fresh_run_reproduces_submitted_report() -> None:
    result, workspace_copy = run_replay_in_temp()
    assert result.returncode == 0, (
        "Fresh replay run failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    fresh_report = load_report(workspace_copy / "out" / "launch_report.json")
    submitted_report = load_report()
    assert _stable_report_projection(fresh_report) == _stable_report_projection(
        submitted_report
    ), "Submitted report does not match a fresh replay run on stable report fields"


def test_protocol_semantics_against_public_inputs() -> None:
    model = build_reference_model(SPEC_ROOT)
    report = load_report()
    state = run_query_state(REPORT_PATH)

    assert _as_int(report["pair"]["fee_bps"]) == model.final_fee_bps
    assert report["governance_token"]["cap"] == model.governance_cap
    assert _as_int(report["governance_token"]["decimals"]) == model.governance_decimals
    assert report["reward_program"]["total_funded"] == str(model.total_reward_funding)
    assert _as_int(report["reward_program"]["rewards_duration_seconds"]) == model.reward_duration_seconds

    total_claimed = int(report["reward_program"]["total_claimed"])
    total_funded = int(report["reward_program"]["total_funded"])
    assert 0 <= total_claimed <= total_funded, "Rewards claimed cannot exceed rewards funded"

    proposal = _proposal_status(report)
    assert proposal is not None, "Expected a governance proposal status block"
    assert proposal["queued"] is True, "Proposal should be queued before execution"
    assert proposal["executed"] is True, "Proposal should be executed in the replay"
    for_votes = int(proposal.get("for_votes", proposal.get("forVotes")))
    against_votes = int(proposal.get("against_votes", proposal.get("againstVotes")))
    assert for_votes >= model.governance_quorum_votes
    assert for_votes > against_votes

    expected_steps = model.scenario_step_ids
    observed_steps = [item["step_id"] for item in report["scenario_results"]]
    assert observed_steps == expected_steps, "scenario_results ordering must follow scenario_replay.json"

    assert state["monotonic_k_on_swaps"] is True, "Swap flow should preserve non-decreasing reserve product"


def test_required_actions_were_executed() -> None:
    model = build_reference_model(SPEC_ROOT)
    must_have_actions = {
        "seed_pair",
        "fund_rewards",
        "stake_lp",
        "claim_rewards",
        "delegate_votes",
        "propose_fee_update",
        "queue",
        "execute",
    }
    assert must_have_actions.issubset(set(model.scenario_actions)), "Scenario input is missing required action types"

    report = load_report()
    observed_actions = [item["action"] for item in report["scenario_results"]]
    assert must_have_actions.issubset(set(observed_actions)), "Report replay is missing required action types"
