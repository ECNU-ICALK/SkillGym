from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


DECISION_ORDER = {
    "allow": 0,
    "allow_with_conditions": 1,
    "review_required": 2,
    "reject": 3,
}

MEASURE_SPECS = {
    "allowlist_gate": {
        "files": ["CollateralRegistry.sol", "CollateralVault.sol"],
        "supported_patterns": [
            "mapping(address => bool) public allowedCollateral",
            'require(registry.allowedCollateral(token), "token-not-allowed")',
        ],
        "partial_patterns": [],
    },
    "safe_transfer_wrapper": {
        "files": ["CollateralVault.sol"],
        "supported_patterns": [
            "using SafeERC20 for IERC20",
            ".safeTransferFrom(",
        ],
        "partial_patterns": [
            ".transferFrom(",
        ],
    },
    "balance_delta_check": {
        "files": ["CollateralVault.sol"],
        "supported_patterns": [
            "balanceBefore",
            "balanceAfter",
            "receivedAssets = balanceAfter - balanceBefore",
        ],
        "partial_patterns": [
            "balanceBefore",
            "balanceAfter",
        ],
    },
    "decimals_normalization": {
        "files": ["CollateralNormalizer.sol", "CollateralVault.sol"],
        "supported_patterns": [
            "function scaleToWad",
            "registry.collateralDecimals(token)",
        ],
        "partial_patterns": [
            "collateralDecimals",
        ],
    },
    "approval_reset_flow": {
        "files": ["ApprovalHelper.sol"],
        "supported_patterns": [
            "safeApprove(spender, 0)",
            "safeApprove(spender, amount)",
        ],
        "partial_patterns": [
            "safeApprove(spender, amount)",
        ],
    },
    "callback_reentrancy_guard": {
        "files": ["CollateralVault.sol"],
        "supported_patterns": [
            "is ReentrancyGuard",
            "nonReentrant",
        ],
        "partial_patterns": [
            "nonReentrant",
        ],
    },
    "upgrade_watch": {
        "files": ["ImplementationWatchtower.sol"],
        "supported_patterns": [
            'require(expectedCodehash[token] == extcodehash(token), "implementation-changed")',
        ],
        "partial_patterns": [
            "event TokenImplementationObserved",
            "extcodehash(token)",
        ],
    },
    "pause_blocklist_runbook": {
        "files": ["CollateralRegistry.sol", "CollateralVault.sol"],
        "supported_patterns": [
            "mapping(address => bool) public blockedCollateral",
            'require(!registry.blockedCollateral(token), "token-blocked")',
        ],
        "partial_patterns": [
            "blockedCollateral",
        ],
    },
    "share_price_recalc": {
        "files": ["CollateralVault.sol"],
        "supported_patterns": [
            "syncExternalBalance",
            "rebaseCheckpoint",
        ],
        "partial_patterns": [],
    },
}

BEHAVIOR_RULES = [
    {
        "finding_id": "missing_return_value",
        "profile_key": "missing_return_value",
        "finding_group": "transfer-semantics",
        "severity": "high",
        "protocol_requirement": "safe_transfer_wrapper",
        "integration_impact": "Transfers may omit a boolean return value, so adapters must use wrappers that treat non-reverting no-return calls safely.",
    },
    {
        "finding_id": "fee_on_transfer",
        "profile_key": "fee_on_transfer",
        "finding_group": "transfer-semantics",
        "severity": "high",
        "protocol_requirement": "balance_delta_check",
        "integration_impact": "Received balances may be lower than the requested transfer amount, so the vault must account for actual receipts.",
    },
    {
        "finding_id": "balance_drift",
        "profile_key": "balance_drift",
        "finding_group": "share-accounting",
        "severity": "critical",
        "protocol_requirement": "share_price_recalc",
        "integration_impact": "Balances may change outside user-triggered transfers, which can break share accounting unless external balance changes are resynchronized.",
    },
    {
        "finding_id": "blocklist_or_pause",
        "profile_key": "blocklist_or_pause",
        "finding_group": "admin-controls",
        "severity": "high",
        "protocol_requirement": "pause_blocklist_runbook",
        "integration_impact": "Central operators may pause or block addresses, so collateral handling needs an explicit operational response path.",
    },
    {
        "finding_id": "upgradeable_or_replaceable",
        "profile_key": "upgradeable_or_replaceable",
        "finding_group": "admin-controls",
        "severity": "high",
        "protocol_requirement": "upgrade_watch",
        "integration_impact": "Token behavior may change after deployment, so the protocol must monitor implementation changes before trusting prior assumptions.",
    },
    {
        "finding_id": "unusual_decimals",
        "profile_key": "derive:decimals_not_18",
        "finding_group": "precision",
        "severity": "medium",
        "protocol_requirement": "decimals_normalization",
        "integration_impact": "Non-18-decimal collateral requires normalization before share math and accounting summaries.",
    },
    {
        "finding_id": "approval_edgecase",
        "profile_key": "approval_edgecase",
        "finding_group": "approval-flow",
        "severity": "medium",
        "protocol_requirement": "approval_reset_flow",
        "integration_impact": "Legacy allowance behavior may require zero-reset approval flows before a new approval can be applied.",
    },
    {
        "finding_id": "hook_or_callback_risk",
        "profile_key": "hook_or_callback_risk",
        "finding_group": "external-callbacks",
        "severity": "high",
        "protocol_requirement": "callback_reentrancy_guard",
        "integration_impact": "Token transfers may invoke callbacks or hooks, so the vault must guard against reentrant state changes during collateral movement.",
    },
]

DECISION_POLICY = {
    "baseline_decision": "allow",
    "supported_behavior_decisions": {
        "missing_return_value": "allow_with_conditions",
        "fee_on_transfer": "allow_with_conditions",
        "hook_or_callback_risk": "allow_with_conditions",
        "unusual_decimals": "allow_with_conditions",
        "approval_edgecase": "allow_with_conditions",
    },
    "reject_if_coverage_not_supported": [
        "fee_on_transfer",
        "balance_drift",
        "hook_or_callback_risk",
    ],
    "review_if_coverage_not_supported": [
        "blocklist_or_pause",
        "upgradeable_or_replaceable",
    ],
    "review_if_coverage_missing": [
        "missing_return_value",
        "approval_edgecase",
    ],
}


def load_policy(data_root: Path) -> dict:
    return json.loads((data_root / "listing_policy.json").read_text(encoding="utf-8"))


def load_token_profiles(data_root: Path) -> list[dict]:
    profiles = []
    for path in sorted((data_root / "token_profiles").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = path
        profiles.append(payload)
    return profiles


def _line_refs_for_pattern(text: str, path: Path, pattern: str) -> list[str]:
    refs: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            refs.append(f"protocol/contracts/{path.name}:{line_number}")
    return refs


def _elevate_decision(current: str, candidate: str) -> str:
    return candidate if DECISION_ORDER[candidate] > DECISION_ORDER[current] else current


def collect_behavior_findings(policy: dict, profiles: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    all_findings: list[dict] = []
    findings_by_token: dict[str, list[dict]] = {}

    for profile in profiles:
        token_findings: list[dict] = []
        for rule in BEHAVIOR_RULES:
            profile_key = rule["profile_key"]
            if profile_key == "derive:decimals_not_18":
                active = int(profile["decimals"]) != 18
            else:
                active = bool(profile["behaviors"].get(profile_key, False))
            if not active:
                continue

            profile_ref = f"data/token_profiles/{profile['_path'].name}#{rule['finding_id']}"
            finding = {
                "token_id": profile["token_id"],
                "symbol": profile["symbol"],
                "finding_id": rule["finding_id"],
                "finding_group": rule["finding_group"],
                "severity": rule["severity"],
                "integration_impact": rule["integration_impact"],
                "protocol_requirement": rule["protocol_requirement"],
                "evidence_refs": [profile_ref],
            }
            token_findings.append(finding)
            all_findings.append(finding)

        findings_by_token[profile["token_id"]] = token_findings

    return all_findings, findings_by_token


def scan_protocol_coverage(policy: dict, contracts_root: Path, findings_by_token: dict[str, list[dict]]) -> dict[str, dict]:
    contract_cache = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(contracts_root.glob("*.sol"))
    }

    covered_tokens_map: dict[str, set[str]] = {measure_id: set() for measure_id in policy["protocol_measure_order"]}
    for token_id, findings in findings_by_token.items():
        covered_tokens_map["allowlist_gate"].add(token_id)
        for finding in findings:
            covered_tokens_map[finding["protocol_requirement"]].add(token_id)

    requirements = {item["measure_id"]: item["requirement"] for item in policy["protocol_measures"]}

    coverage: dict[str, dict] = {}
    for measure_id in policy["protocol_measure_order"]:
        spec = MEASURE_SPECS[measure_id]

        supported_hits: list[str] = []
        partial_hits: list[str] = []
        supported_patterns = spec["supported_patterns"]
        partial_patterns = spec["partial_patterns"]

        for file_name in spec["files"]:
            text = contract_cache.get(file_name, "")
            file_path = Path(file_name)
            for pattern in supported_patterns:
                supported_hits.extend(_line_refs_for_pattern(text, file_path, pattern))
            for pattern in partial_patterns:
                partial_hits.extend(_line_refs_for_pattern(text, file_path, pattern))

        supported = all(
            any(pattern in contract_cache.get(file_name, "") for file_name in spec["files"])
            for pattern in supported_patterns
        )
        partial = bool(partial_hits) or bool(supported_hits)

        if supported:
            status = "supported"
            refs = sorted(dict.fromkeys(supported_hits))
        elif partial:
            status = "partial"
            refs = sorted(dict.fromkeys(supported_hits + partial_hits))
        else:
            status = "missing"
            refs = []

        coverage[measure_id] = {
            "measure_id": measure_id,
            "requirement": requirements[measure_id],
            "coverage_status": status,
            "protocol_location": ";".join(refs),
            "evidence_refs": refs,
            "covered_tokens": sorted(covered_tokens_map[measure_id]),
        }

    return coverage


def assign_token_decisions(
    policy: dict,
    profiles: list[dict],
    findings_by_token: dict[str, list[dict]],
    coverage: dict[str, dict],
) -> list[dict]:
    risk_by_decision = policy["overall_risk_by_decision"]
    results: list[dict] = []

    for profile in profiles:
        token_id = profile["token_id"]
        findings = findings_by_token[token_id]
        required_measures = []
        for measure_id in policy["always_required_measures"]:
            if measure_id not in required_measures:
                required_measures.append(measure_id)
        for measure_id in policy["protocol_measure_order"]:
            if any(f["protocol_requirement"] == measure_id for f in findings) and measure_id not in required_measures:
                required_measures.append(measure_id)

        decision = DECISION_POLICY["baseline_decision"]
        blockers: list[str] = []
        decision_refs: list[str] = [f"data/token_profiles/{profile['_path'].name}"]

        for finding in findings:
            measure_id = finding["protocol_requirement"]
            measure_cov = coverage[measure_id]["coverage_status"]
            finding_id = finding["finding_id"]

            if finding_id in DECISION_POLICY["reject_if_coverage_not_supported"] and measure_cov != "supported":
                decision = _elevate_decision(decision, "reject")
                blockers.append(f"{finding_id}({measure_id}={measure_cov})")
            elif finding_id in DECISION_POLICY["review_if_coverage_not_supported"] and measure_cov != "supported":
                decision = _elevate_decision(decision, "review_required")
                blockers.append(f"{finding_id}({measure_id}={measure_cov})")
            elif finding_id in DECISION_POLICY["review_if_coverage_missing"] and measure_cov == "missing":
                decision = _elevate_decision(decision, "review_required")
                blockers.append(f"{finding_id}({measure_id}=missing)")
            elif finding_id in DECISION_POLICY["supported_behavior_decisions"] and measure_cov == "supported":
                decision = _elevate_decision(decision, DECISION_POLICY["supported_behavior_decisions"][finding_id])
                blockers.append(f"{finding_id}({measure_id}=supported)")

            decision_refs.extend(finding["evidence_refs"])
            decision_refs.extend(coverage[measure_id]["evidence_refs"])

        blocking_conditions = ";".join(dict.fromkeys(blockers))
        evidence_refs = ";".join(dict.fromkeys(ref for ref in decision_refs if ref))

        results.append(
            {
                "token_id": token_id,
                "symbol": profile["symbol"],
                "decision": decision,
                "overall_risk": risk_by_decision[decision],
                "blocking_conditions": blocking_conditions,
                "required_protocol_measures": ";".join(required_measures),
                "evidence_refs": evidence_refs,
            }
        )

    return results


def findings_frame(policy: dict, findings_by_token: dict[str, list[dict]], coverage: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for token_id in sorted(findings_by_token):
        for finding in findings_by_token[token_id]:
            measure_id = finding["protocol_requirement"]
            coverage_status = coverage[measure_id]["coverage_status"]
            integration_impact = finding["integration_impact"]
            if coverage_status not in integration_impact.lower():
                integration_impact = f"{integration_impact} Protocol coverage is {coverage_status}."
            rows.append(
                {
                    "token_id": finding["token_id"],
                    "symbol": finding["symbol"],
                    "finding_id": finding["finding_id"],
                    "finding_group": finding["finding_group"],
                    "severity": finding["severity"],
                    "integration_impact": integration_impact,
                    "protocol_requirement": finding["protocol_requirement"],
                    "evidence_refs": ";".join(finding["evidence_refs"]),
                }
            )
    return pd.DataFrame(rows, columns=policy["output_contract"]["token_behavior_findings_columns"])


def coverage_frame(policy: dict, coverage: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for measure_id in policy["protocol_measure_order"]:
        item = coverage[measure_id]
        rows.append(
            {
                "measure_id": measure_id,
                "requirement": item["requirement"],
                "protocol_location": item["protocol_location"],
                "coverage_status": item["coverage_status"],
                "covered_tokens": ";".join(item["covered_tokens"]),
                "evidence_refs": ";".join(item["evidence_refs"]),
            }
        )
    return pd.DataFrame(rows, columns=policy["output_contract"]["guardrail_coverage_columns"])


def decisions_frame(policy: dict, decisions: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(decisions, columns=policy["output_contract"]["token_decisions_columns"])
    return frame.sort_values(["token_id"]).reset_index(drop=True)


def build_evidence_index(
    policy: dict,
    profiles: list[dict],
    decisions: list[dict],
    coverage: dict[str, dict],
    contracts_root: Path,
) -> dict:
    protocol_files = []
    for path in sorted(contracts_root.glob("*.sol")):
        protocol_files.append(
            {
                "path": f"protocol/contracts/{path.name}",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    candidate_tokens = {}
    for profile in profiles:
        candidate_tokens[profile["token_id"]] = {
            "path": f"data/token_profiles/{profile['_path'].name}",
            "symbol": profile["symbol"],
            "decimals": profile["decimals"],
        }

    decision_map = {}
    for row in decisions:
        decision_map[row["token_id"]] = {
            "decision": row["decision"],
            "overall_risk": row["overall_risk"],
            "blocking_conditions": row["blocking_conditions"],
            "required_protocol_measures": row["required_protocol_measures"].split(";"),
        }

    coverage_map = {}
    for measure_id, item in coverage.items():
        coverage_map[measure_id] = {
            "coverage_status": item["coverage_status"],
            "protocol_location": item["protocol_location"],
            "covered_tokens": item["covered_tokens"],
            "evidence_refs": item["evidence_refs"],
        }

    return {
        "protocol_files": protocol_files,
        "candidate_tokens": candidate_tokens,
        "decisions": decision_map,
        "coverage": coverage_map,
        "notes": [
            f"{policy['protocol_name']} onboarding review generated from local policy, token profiles, and Solidity source."
        ],
    }
