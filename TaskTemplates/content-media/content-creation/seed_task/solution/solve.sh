#!/bin/bash
set -euo pipefail

cat > /app/workspace/build_content_pack.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Renewable Capacity Momentum 2025 publication pack.")
    parser.add_argument("--campaign-root", default="/app/campaign")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def make_context(campaign_root: Path) -> dict:
    contract = load_json(campaign_root / "brief" / "channel_contract.json")
    source_manifest = load_json(campaign_root / "data" / "source_manifest.json")
    claims_payload = load_json(campaign_root / "data" / "claim_bank.json")
    claims = {claim["id"]: claim for claim in claims_payload["claims"]}
    return {
        "contract": contract,
        "sources": {item["id"]: item for item in source_manifest["sources"]},
        "claims": claims,
    }


def c(ctx: dict, claim_id: str) -> dict:
    return ctx["claims"][claim_id]


def newsletter_text(ctx: dict) -> str:
    c01 = c(ctx, "C01")["data"]
    c02 = c(ctx, "C02")["data"]
    c03 = c(ctx, "C03")["data"]
    c04 = c(ctx, "C04")["data"]
    c05 = c(ctx, "C05")["data"]
    c06 = c(ctx, "C06")["data"]
    title = ctx["contract"]["campaign_title"]
    body = (
        f"# {title}: Record Additions, Harder Execution\n\n"
        f"The shift is already visible in the numbers. Global renewable power capacity reached {c01['capacity_gw']:,} GW in {c01['metric_year']} after a {c01['annual_addition_gw']:,} GW annual increase, and renewables accounted for {c02['expansion_share_pct']:.1f}% of total power capacity expansion with {c02['annual_growth_pct']:.1f}% annual growth. That is real momentum, not a marginal improvement.\n\n"
        f"The next step is harder. The IEA stocktake still keeps {c03['benchmark_gw']:,} GW in view as the benchmark for the tripling pledge by {c03['target_year']}, while current government ambitions land closer to {c04['ambition_gw']:,} GW. The gap is no longer abstract. It is the distance between a record build year and a deployment pace that can hold through the rest of the decade.\n\n"
        f"The mix matters too. The IEA expects solar PV to deliver {c05['share_text']} of the year's increase in global renewable capacity, which helps explain why the scale has changed so quickly. But scale on paper does not clear projects into operation. Long permitting waits, grid investment gaps, and high financing costs still slow deployment, especially where system integration and wider build-out remain unresolved.\n\n"
        f"That is why the headline number is not the whole story. Tripling renewable capacity by {c03['target_year']} would {c06['impact_text']}. The useful reading of {c01['metric_year']} is narrower and more demanding: momentum is real, the {c03['target_year']} benchmark remains out of reach on current ambitions, and the next decision sits in grids, permitting, and finance.\n"
    )
    return body


def linkedin_text(ctx: dict) -> str:
    c01 = c(ctx, "C01")["data"]
    c04 = c(ctx, "C04")["data"]
    c03 = c(ctx, "C03")["data"]
    return (
        f"{c01['metric_year']} settled one part of the argument. Global renewable power capacity reached {c01['capacity_gw']:,} GW after a {c01['annual_addition_gw']:,} GW annual increase. The market can scale.\n\n"
        f"The harder conclusion is operational. The IEA stocktake still puts current government ambitions at about {c04['ambition_gw']:,} GW by {c04['target_year']}, well short of the {c03['benchmark_gw']:,} GW benchmark tied to the tripling pledge.\n\n"
        "For business readers, that shifts the takeaway. The limiting factor is less about whether renewables can add capacity and more about whether projects can clear the system around them. Long permitting waits, grid investment gaps, and high financing costs are now strategy issues, not side notes.\n\n"
        "The companies and institutions that reduce those frictions will matter as much as the next headline installation record. Record additions changed the baseline; delivery capacity now determines whether momentum becomes a credible 2030 pathway."
    )


def thread_text(ctx: dict) -> str:
    c01 = c(ctx, "C01")["data"]
    c02 = c(ctx, "C02")["data"]
    c05 = c(ctx, "C05")["data"]
    c08 = c(ctx, "C08")["data"]
    c09 = c(ctx, "C09")["data"]
    c03 = c(ctx, "C03")["data"]
    c04 = c(ctx, "C04")["data"]
    return (
        f"1. Renewable capacity did not edge up in {c01['metric_year']}. It jumped. Global renewable power capacity reached {c01['capacity_gw']:,} GW after a {c01['annual_addition_gw']:,} GW annual increase. That is the scale shift behind this briefing.\n\n"
        f"2. Renewables also accounted for {c02['expansion_share_pct']:.1f}% of total power capacity expansion in {c01['metric_year']}, with {c02['annual_growth_pct']:.1f}% annual growth. The build story is no longer marginal. It is becoming the center of new power additions.\n\n"
        f"3. Solar is still the main engine. It is on course to deliver {c05['share_text']} of the year's increase, while world solar rose from {c08['solar_start_twh']:,} TWh in {c08['start_year']} to {c08['solar_end_twh']:,} TWh in {c08['end_year']}.\n\n"
        f"4. {c09['country']} stays central to that momentum. In the bundled {c09['year']} OWID row, {c09['country']} records {c09['solar_twh']:,} TWh of solar generation and {c09['wind_twh']:,} TWh of wind generation.\n\n"
        f"5. But record additions do not automatically deliver the {c03['target_year']} pledge. The IEA stocktake keeps {c03['benchmark_gw']:,} GW in view for tripling by {c03['target_year']}, while current government ambitions sit closer to {c04['ambition_gw']:,} GW.\n\n"
        "6. That makes the next constraint practical, not rhetorical: long permitting waits, grid investment gaps, and high financing costs still slow deployment. The build story now depends on execution capacity."
    )


def video_text(ctx: dict) -> str:
    c01 = c(ctx, "C01")["data"]
    c02 = c(ctx, "C02")["data"]
    c08 = c(ctx, "C08")["data"]
    c09 = c(ctx, "C09")["data"]
    c03 = c(ctx, "C03")["data"]
    c04 = c(ctx, "C04")["data"]
    c06 = c(ctx, "C06")["data"]
    return (
        "Scene 1\n"
        f"Voiceover: {c01['metric_year']} reset the renewable build baseline. The pack puts total renewable power capacity at {c01['capacity_gw']:,} GW after a {c01['annual_addition_gw']:,} GW increase in a single year.\n"
        f"On-screen text: {c01['capacity_gw']:,} GW total renewable capacity | +{c01['annual_addition_gw']:,} GW in {c01['metric_year']}\n\n"
        "Scene 2\n"
        f"Voiceover: This was not a niche gain. Renewables made up {c02['expansion_share_pct']:.1f}% of total power capacity expansion, with {c02['annual_growth_pct']:.1f}% annual growth.\n"
        f"On-screen text: {c02['expansion_share_pct']:.1f}% of capacity expansion | {c02['annual_growth_pct']:.1f}% annual growth\n\n"
        "Scene 3\n"
        f"Voiceover: The generation trend confirms the build story. World solar moves from {c08['solar_start_twh']:,} TWh in {c08['start_year']} to {c08['solar_end_twh']:,} TWh in {c08['end_year']}, while world wind climbs from {c08['wind_start_twh']:,} TWh to {c08['wind_end_twh']:,} TWh.\n"
        f"On-screen text: World solar {c08['solar_start_twh']:,} to {c08['solar_end_twh']:,} TWh | World wind {c08['wind_start_twh']:,} to {c08['wind_end_twh']:,} TWh\n\n"
        "Scene 4\n"
        f"Voiceover: One country still carries a large share of that scale. The bundled {c09['year']} row for {c09['country']} shows {c09['solar_twh']:,} TWh of solar generation and {c09['wind_twh']:,} TWh of wind generation.\n"
        f"On-screen text: {c09['country']} {c09['year']} | Solar {c09['solar_twh']:,} TWh | Wind {c09['wind_twh']:,} TWh\n\n"
        "Scene 5\n"
        f"Voiceover: The record year still leaves a benchmark gap. The IEA keeps {c03['benchmark_gw']:,} GW in view for the {c03['target_year']} tripling path, while current government ambitions sit closer to {c04['ambition_gw']:,} GW.\n"
        f"On-screen text: {c03['target_year']} benchmark {c03['benchmark_gw']:,} GW | Current ambitions about {c04['ambition_gw']:,} GW\n\n"
        "Scene 6\n"
        f"Voiceover: That shortfall changes the closing question. Tripling renewable capacity by {c03['target_year']} would {c06['impact_text']}, but only if grid investment, permitting, and financing move at the same speed as deployment.\n"
        "On-screen text: Next bottlenecks | Grid investment | Permitting | Financing\n"
    )


def manifest(ctx: dict) -> dict:
    contract = ctx["contract"]
    sources_used = [item["id"] for item in ctx["sources"].values()]
    deliverables = [
        {
            "file": "newsletter_intro.md",
            "channel": "newsletter",
            "primary_angle": "Record renewable additions signal real momentum, but the 2030 pathway still hinges on execution.",
            "target_reader": "Write for readers who already follow climate and energy developments and want a sharp lead-in to the larger briefing.",
            "claims_used": ["C01", "C02", "C03", "C04", "C05", "C07", "C06"],
            "cta": "Continue into the full briefing for the gap and constraint behind the record year."
        },
        {
            "file": "linkedin_post.md",
            "channel": "linkedin",
            "primary_angle": "For business readers, the renewable story has shifted from proof of scale to proof of delivery.",
            "target_reader": "Write for a broader business audience that still expects one concrete operating takeaway rather than a long recap.",
            "claims_used": ["C01", "C04", "C03", "C07"],
            "cta": "Carry the takeaway into planning around grids, permitting, and financing."
        },
        {
            "file": "thread.md",
            "channel": "thread",
            "primary_angle": "Move from record scale to the 2030 gap and the execution bottlenecks in six compact steps.",
            "target_reader": "Keep each post compact and additive for a public short-form reading flow.",
            "claims_used": ["C01", "C02", "C05", "C09", "C03", "C04", "C07"],
            "cta": "Use the thread to frame the briefing's momentum-to-constraint story in public short form."
        },
        {
            "file": "video_script.md",
            "channel": "video",
            "primary_angle": "Build a 60-second explainer that moves from record additions to the unresolved 2030 delivery gap.",
            "target_reader": "Write for a 60-second explainer built around the bundled visual cue sheet.",
            "claims_used": ["C01", "C02", "C08", "C09", "C03", "C04", "C06", "C07"],
            "cta": "Close on the execution agenda of grid, permitting, and financing fixes."
        }
    ]

    notes = []
    for item in deliverables:
        if item["file"] in {"newsletter_intro.md", "linkedin_post.md"}:
            section_labels = ["body"]
        elif item["file"] == "thread.md":
            section_labels = [f"post_{index}" for index in range(1, 7)]
        else:
            section_labels = [f"scene_{index}" for index in range(1, 7)]
        for index, claim_id in enumerate(item["claims_used"]):
            section = section_labels[min(index, len(section_labels) - 1)]
            claim = ctx["claims"][claim_id]
            notes.append(
                {
                    "file": item["file"],
                    "section": section,
                    "claim_id": claim_id,
                    "source_id": claim["source_id"],
                    "evidence": claim["statement"],
                }
            )

    return {
        "campaign_title": contract["campaign_title"],
        "audience": contract["audience"],
        "core_messages": contract["core_messages"],
        "deliverables": deliverables,
        "sources_used": sources_used,
        "claim_support_notes": notes,
    }


def main() -> int:
    args = parse_args()
    campaign_root = Path(args.campaign_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    ctx = make_context(campaign_root)
    (output_root / "newsletter_intro.md").write_text(newsletter_text(ctx), encoding="utf-8")
    (output_root / "linkedin_post.md").write_text(linkedin_text(ctx), encoding="utf-8")
    (output_root / "thread.md").write_text(thread_text(ctx), encoding="utf-8")
    (output_root / "video_script.md").write_text(video_text(ctx), encoding="utf-8")
    (output_root / "content_manifest.json").write_text(json.dumps(manifest(ctx), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x /app/workspace/build_content_pack.py
python3 /app/workspace/build_content_pack.py --campaign-root /app/campaign --output-root /app/output
