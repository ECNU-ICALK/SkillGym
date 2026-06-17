#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

function readReport(reportPath) {
  const absolute = path.resolve(reportPath);
  return JSON.parse(fs.readFileSync(absolute, "utf8"));
}

function toBigInt(value) {
  if (typeof value === "bigint") return value;
  if (typeof value === "number") return BigInt(value);
  return BigInt(String(value));
}

function computeMonotonicKOnSwaps(scenarioResults) {
  let previous = null;
  for (const step of scenarioResults) {
    const action = String(step.action || "");
    const isSwap = action === "swap_exact_in" || action === "swap";
    if (!isSwap) {
      previous = step;
      continue;
    }
    if (!previous || !previous.pair || !step.pair) return false;
    const kBefore = toBigInt(previous.pair.reserve0) * toBigInt(previous.pair.reserve1);
    const kAfter = toBigInt(step.pair.reserve0) * toBigInt(step.pair.reserve1);
    if (kAfter < kBefore) return false;
    previous = step;
  }
  return true;
}

function main() {
  const reportPath = process.argv[2];
  if (!reportPath) {
    throw new Error("usage: query_state.js <launch_report.json>");
  }

  const report = readReport(reportPath);
  const scenarioResults = Array.isArray(report.scenario_results) ? report.scenario_results : [];
  const proposal = report.governance_token && report.governance_token.proposal_status;

  const payload = {
    pair: {
      fee_bps: Number(report.pair.fee_bps),
      reserve0: String(report.pair.reserve0),
      reserve1: String(report.pair.reserve1),
      total_lp_supply: String(report.pair.total_lp_supply),
    },
    rewards: {
      total_funded: String(report.reward_program.total_funded),
      total_claimed: String(report.reward_program.total_claimed),
      total_staked: String(report.reward_program.total_staked),
      duration_seconds: Number(report.reward_program.rewards_duration_seconds),
    },
    governance: {
      proposal_count: Number(report.governance_token.proposal_count),
      proposal_queued: proposal ? Boolean(proposal.queued) : false,
      proposal_executed: proposal ? Boolean(proposal.executed) : false,
      for_votes: proposal ? String(proposal.for_votes) : "0",
      against_votes: proposal ? String(proposal.against_votes) : "0",
    },
    monotonic_k_on_swaps: computeMonotonicKOnSwaps(scenarioResults),
    scenario_steps: scenarioResults.map((item) => ({
      step_id: item.step_id,
      action: item.action,
    })),
  };

  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

main();
