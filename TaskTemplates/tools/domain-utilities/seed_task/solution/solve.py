from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/workspace/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
PREFERRED_STYLE_TAGS = {"workflow", "automation", "deployment", "observability", "infra"}
WEIGHTS = {
    "brandability": 0.33,
    "pronounceability": 0.24,
    "developer_fit": 0.31,
    "style_match_per_hit": 0.12,
}
TLD_BONUS = {
    "com": 0.58,
    "ai": 0.52,
    "tech": 0.40,
    "xyz": 0.26,
}
LENGTH_BONUS_RULES = [
    {"min": 8, "max": 10, "bonus": 0.16},
    {"min": 11, "max": 12, "bonus": 0.08},
    {"min": 13, "max": 14, "bonus": 0.00},
]


def load_policy() -> dict[str, object]:
    return json.loads((DATA_DIR / "tld_policy.json").read_text(encoding="utf-8"))


def load_candidates() -> pd.DataFrame:
    candidates = pd.read_csv(DATA_DIR / "candidate_pool.csv")
    candidates["style_tags"] = candidates["style_tags"].map(lambda value: [part.strip() for part in str(value).split(";") if part.strip()])
    candidates["length"] = candidates["base_name"].str.len()
    return candidates


def length_bonus(length: int, rules: list[dict[str, object]]) -> float:
    for rule in rules:
        if int(rule["min"]) <= length <= int(rule["max"]):
            return float(rule["bonus"])
    return 0.0


def build_audit() -> pd.DataFrame:
    policy = load_policy()
    snapshot = pd.read_csv(DATA_DIR / "availability_snapshot.csv")
    candidates = load_candidates()
    tld_order = {value: idx for idx, value in enumerate(policy["allowed_tlds"])}

    merged = snapshot.merge(candidates, on="base_name", how="left", validate="many_to_one")
    merged["style_match_count"] = merged["style_tags"].map(lambda values: sum(1 for value in values if value in PREFERRED_STYLE_TAGS))
    merged["length_bonus"] = merged["length"].map(lambda value: length_bonus(int(value), LENGTH_BONUS_RULES))
    merged["tld_bonus"] = merged["tld"].map(lambda value: float(TLD_BONUS[value]))
    merged["score"] = (
        merged["brandability"] * float(WEIGHTS["brandability"])
        + merged["pronounceability"] * float(WEIGHTS["pronounceability"])
        + merged["developer_fit"] * float(WEIGHTS["developer_fit"])
        + merged["style_match_count"] * float(WEIGHTS["style_match_per_hit"])
        + merged["length_bonus"]
        + merged["tld_bonus"]
    )
    merged["tld_rank"] = merged["tld"].map(tld_order)
    return merged


def write_audit(audit: pd.DataFrame) -> None:
    policy = load_policy()
    tld_order = {value: idx for idx, value in enumerate(policy["allowed_tlds"])}
    export = audit.copy()
    export["tld_rank"] = export["tld"].map(tld_order)
    export = export.sort_values(["base_name", "tld_rank", "domain"]).reset_index(drop=True)
    export = export[
        [
            "base_name",
            "tld",
            "domain",
            "availability",
            "score",
            "brandability",
            "pronounceability",
            "developer_fit",
            "style_match_count",
            "length_bonus",
            "tld_bonus",
        ]
    ].copy()
    numeric_columns = [
        "score",
        "brandability",
        "pronounceability",
        "developer_fit",
        "length_bonus",
        "tld_bonus",
    ]
    export[numeric_columns] = export[numeric_columns].astype(float).round(3)
    export["style_match_count"] = export["style_match_count"].astype(int)
    export.to_csv(OUTPUT_DIR / "availability_audit.csv", index=False)


def write_shortlist(audit: pd.DataFrame) -> None:
    policy = load_policy()
    candidates = load_candidates().set_index("base_name")
    available = audit[audit["availability"] == "available"].copy()
    available = available.sort_values(["base_name", "score", "tld_rank", "domain"], ascending=[True, False, True, True])
    best_available = available.groupby("base_name", as_index=False).first()
    best_available = best_available.sort_values(["score", "base_name"], ascending=[False, True]).reset_index(drop=True)

    shortlist_size = int(policy["shortlist_size"])
    runner_up_size = int(policy["runner_up_size"])
    shortlist_rows = best_available.iloc[:shortlist_size]
    runner_rows = best_available.iloc[shortlist_size:shortlist_size + runner_up_size]

    taken = audit[audit["availability"] == "taken"].copy()
    taken = taken.sort_values(["score", "tld_rank", "domain"], ascending=[False, True, True]).reset_index(drop=True)
    taken_domains = taken.iloc[: int(policy["taken_showcase_size"])]["domain"].tolist()

    shortlist: list[dict[str, object]] = []
    for rank, row in enumerate(shortlist_rows.itertuples(index=False), start=1):
        shortlist.append(
            {
                "rank": rank,
                "domain": row.domain,
                "base_name": row.base_name,
                "tld": row.tld,
                "availability": "available",
                "score": round(float(row.score), 3),
                "length": int(len(row.base_name)),
                "style_tags": candidates.loc[row.base_name, "style_tags"],
                "why_it_fits": f"{row.base_name} keeps a compact developer-tool tone and pairs well with .{row.tld} for this launch brief.",
            }
        )

    top_pick = shortlist[0]["domain"]
    payload = {
        "project_slug": policy["project_slug"],
        "evaluated_tlds": list(policy["allowed_tlds"]),
        "shortlist": shortlist,
        "runner_ups": runner_rows["domain"].tolist(),
        "rejected_taken_domains": taken_domains,
        "top_pick_summary": f"{top_pick} leads the pack because it combines the strongest available score with a compact base name and clear developer-tool positioning.",
    }
    (OUTPUT_DIR / "domain_shortlist.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    write_audit(audit)
    write_shortlist(audit)


if __name__ == "__main__":
    main()
