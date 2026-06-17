from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


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


def _load_policy(data_root: Path) -> dict:
    return json.loads((data_root / "listing_policy.json").read_text(encoding="utf-8"))


def _load_profiles(data_root: Path) -> list[dict]:
    profiles = []
    for path in sorted((data_root / "token_profiles").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = path
        profiles.append(payload)
    return profiles


def _matching_line_refs(path: Path, patterns: list[str]) -> list[str]:
    refs: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pattern in patterns:
        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                refs.append(f"protocol/contracts/{path.name}:{line_number}")
    return refs


def _findings_for_profile(profile: dict) -> list[dict]:
    findings = []
    for rule in BEHAVIOR_RULES:
        key = rule["profile_key"]
        if key == "derive:decimals_not_18":
            active = int(profile["decimals"]) != 18
        else:
            active = bool(profile["behaviors"].get(key, False))
        if not active:
            continue
        findings.append(
            {
                "token_id": profile["token_id"],
                "symbol": profile["symbol"],
                "finding_id": rule["finding_id"],
                "finding_group": rule["finding_group"],
                "severity": rule["severity"],
                "integration_impact": rule["integration_impact"],
                "protocol_requirement": rule["protocol_requirement"],
                "evidence_refs": [f"data/token_profiles/{profile['_path'].name}#{rule['finding_id']}"],
            }
        )
    return findings


def _measure_coverage(policy: dict, contracts_root: Path, token_to_findings: dict[str, list[dict]]) -> dict[str, dict]:
    measure_to_tokens: dict[str, set[str]] = {item["measure_id"]: set() for item in policy["protocol_measures"]}
    for token_id, findings in token_to_findings.items():
        for measure_id in policy["always_required_measures"]:
            measure_to_tokens[measure_id].add(token_id)
        for finding in findings:
            measure_to_tokens[finding["protocol_requirement"]].add(token_id)

    requirements = {item["measure_id"]: item["requirement"] for item in policy["protocol_measures"]}

    coverage = {}
    for measure_id in policy["protocol_measure_order"]:
        spec = MEASURE_SPECS[measure_id]
        refs = []
        supported_ok = True
        partial_found = False
        for pattern in spec["supported_patterns"]:
            found = False
            for file_name in spec["files"]:
                path = contracts_root / file_name
                file_refs = _matching_line_refs(path, [pattern])
                if file_refs:
                    found = True
                    refs.extend(file_refs)
            supported_ok = supported_ok and found
        for pattern in spec["partial_patterns"]:
            for file_name in spec["files"]:
                path = contracts_root / file_name
                file_refs = _matching_line_refs(path, [pattern])
                if file_refs:
                    partial_found = True
                    refs.extend(file_refs)

        if supported_ok:
            status = "supported"
        elif partial_found or refs:
            status = "partial"
        else:
            status = "missing"

        refs = sorted(dict.fromkeys(refs))
        coverage[measure_id] = {
            "measure_id": measure_id,
            "requirement": requirements[measure_id],
            "protocol_location": ";".join(refs),
            "coverage_status": status,
            "covered_tokens": sorted(measure_to_tokens[measure_id]),
            "evidence_refs": refs,
        }
    return coverage


def _decision_rank(value: str) -> int:
    return {
        "allow": 0,
        "allow_with_conditions": 1,
        "review_required": 2,
        "reject": 3,
    }[value]


def _resolve_decisions(policy: dict, profiles: list[dict], token_to_findings: dict[str, list[dict]], coverage: dict[str, dict]) -> list[dict]:
    rows = []
    for profile in profiles:
        findings = token_to_findings[profile["token_id"]]
        required_measures = list(policy["always_required_measures"])
        for measure_id in policy["protocol_measure_order"]:
            if any(f["protocol_requirement"] == measure_id for f in findings) and measure_id not in required_measures:
                required_measures.append(measure_id)

        decision = DECISION_POLICY["baseline_decision"]
        blockers = []
        evidence_refs = [f"data/token_profiles/{profile['_path'].name}"]

        for finding in findings:
            finding_id = finding["finding_id"]
            measure_id = finding["protocol_requirement"]
            status = coverage[measure_id]["coverage_status"]

            if finding_id in DECISION_POLICY["reject_if_coverage_not_supported"] and status != "supported":
                if _decision_rank("reject") > _decision_rank(decision):
                    decision = "reject"
                blockers.append(f"{finding_id}({measure_id}={status})")
            elif finding_id in DECISION_POLICY["review_if_coverage_not_supported"] and status != "supported":
                if _decision_rank("review_required") > _decision_rank(decision):
                    decision = "review_required"
                blockers.append(f"{finding_id}({measure_id}={status})")
            elif finding_id in DECISION_POLICY["review_if_coverage_missing"] and status == "missing":
                if _decision_rank("review_required") > _decision_rank(decision):
                    decision = "review_required"
                blockers.append(f"{finding_id}({measure_id}=missing)")
            elif status == "supported" and finding_id in DECISION_POLICY["supported_behavior_decisions"]:
                candidate = DECISION_POLICY["supported_behavior_decisions"][finding_id]
                if _decision_rank(candidate) > _decision_rank(decision):
                    decision = candidate
                blockers.append(f"{finding_id}({measure_id}=supported)")

            evidence_refs.extend(finding["evidence_refs"])
            evidence_refs.extend(coverage[measure_id]["evidence_refs"])

        rows.append(
            {
                "token_id": profile["token_id"],
                "symbol": profile["symbol"],
                "decision": decision,
                "overall_risk": policy["overall_risk_by_decision"][decision],
                "blocking_conditions": ";".join(dict.fromkeys(blockers)),
                "required_protocol_measures": ";".join(required_measures),
                "evidence_refs": ";".join(dict.fromkeys(evidence_refs)),
            }
        )
    return rows


def expected_bundle(task_root: Path) -> dict[str, object]:
    data_root = task_root / "data"
    contracts_root = task_root / "protocol" / "contracts"
    policy = _load_policy(data_root)
    profiles = _load_profiles(data_root)
    token_to_findings = {profile["token_id"]: _findings_for_profile(profile) for profile in profiles}
    coverage = _measure_coverage(policy, contracts_root, token_to_findings)
    decisions = _resolve_decisions(policy, profiles, token_to_findings, coverage)

    findings_rows = []
    for token_id in sorted(token_to_findings):
        for finding in token_to_findings[token_id]:
            findings_rows.append(
                {
                    "token_id": finding["token_id"],
                    "symbol": finding["symbol"],
                    "finding_id": finding["finding_id"],
                    "finding_group": finding["finding_group"],
                    "severity": finding["severity"],
                    "integration_impact": finding["integration_impact"],
                    "protocol_requirement": finding["protocol_requirement"],
                    "evidence_refs": ";".join(finding["evidence_refs"]),
                }
            )

    coverage_rows = []
    for measure_id in policy["protocol_measure_order"]:
        item = coverage[measure_id]
        coverage_rows.append(
            {
                "measure_id": measure_id,
                "requirement": item["requirement"],
                "protocol_location": item["protocol_location"],
                "coverage_status": item["coverage_status"],
                "covered_tokens": ";".join(item["covered_tokens"]),
                "evidence_refs": ";".join(item["evidence_refs"]),
            }
        )

    protocol_files = []
    for path in sorted(contracts_root.glob("*.sol")):
        protocol_files.append(
            {
                "path": f"protocol/contracts/{path.name}",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    evidence = {
        "protocol_files": protocol_files,
        "candidate_tokens": {
            profile["token_id"]: {
                "path": f"data/token_profiles/{profile['_path'].name}",
                "symbol": profile["symbol"],
                "decimals": profile["decimals"],
            }
            for profile in profiles
        },
        "decisions": {
            row["token_id"]: {
                "decision": row["decision"],
                "overall_risk": row["overall_risk"],
                "blocking_conditions": row["blocking_conditions"],
                "required_protocol_measures": row["required_protocol_measures"].split(";"),
            }
            for row in decisions
        },
        "coverage": {
            key: {
                "coverage_status": value["coverage_status"],
                "protocol_location": value["protocol_location"],
                "covered_tokens": value["covered_tokens"],
                "evidence_refs": value["evidence_refs"],
            }
            for key, value in coverage.items()
        },
    }

    return {
        "policy": policy,
        "decisions": pd.DataFrame(decisions, columns=policy["output_contract"]["token_decisions_columns"]).sort_values("token_id").reset_index(drop=True),
        "findings": pd.DataFrame(findings_rows, columns=policy["output_contract"]["token_behavior_findings_columns"]).sort_values(["token_id", "finding_id"]).reset_index(drop=True),
        "coverage": pd.DataFrame(coverage_rows, columns=policy["output_contract"]["guardrail_coverage_columns"]).sort_values("measure_id").reset_index(drop=True),
        "evidence": evidence,
    }
