const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");
const hre = require("hardhat");

const { ethers } = hre;

const ROOT = process.env.TASK_WORKSPACE_ROOT || "/root/workspace";
const SPEC_DIR = path.join(ROOT, "spec");
const OUT_DIR = path.join(ROOT, "out");

function readYaml(name) {
  return yaml.load(fs.readFileSync(path.join(SPEC_DIR, name), "utf8"));
}

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(SPEC_DIR, name), "utf8"));
}

function readCsv(name) {
  const text = fs.readFileSync(path.join(SPEC_DIR, name), "utf8").trim();
  const [headerLine, ...rows] = text.split(/\r?\n/);
  const headers = headerLine.split(",");
  return rows.map((row) => {
    const values = row.split(",");
    const out = {};
    headers.forEach((key, idx) => {
      out[key] = values[idx];
    });
    return out;
  });
}

function str(value) {
  return value.toString();
}

function asBool(support) {
  if (typeof support === "boolean") return support;
  return String(support).toLowerCase() === "for";
}

function getShareAmount(balance, shareBps) {
  return (balance * BigInt(shareBps)) / 10000n;
}

function getActorNames(launchPlan, replaySpec) {
  const names = [];
  const seen = new Set();
  const sources = [
    launchPlan.governance_token.initial_allocations,
    launchPlan.assets.base.initial_allocations,
    launchPlan.assets.quote.initial_allocations,
  ];

  for (const source of sources) {
    for (const name of Object.keys(source)) {
      if (!seen.has(name)) {
        seen.add(name);
        names.push(name);
      }
    }
  }

  for (const step of replaySpec.steps) {
    for (const field of ["actor", "delegatee", "to"]) {
      const name = step[field];
      if (typeof name === "string" && !seen.has(name)) {
        seen.add(name);
        names.push(name);
      }
    }
  }

  return names;
}

function buildActors(signers, actorNames) {
  if (actorNames.length > signers.length) {
    throw new Error(`Need ${actorNames.length} signers but only found ${signers.length}`);
  }
  const actors = {};
  actorNames.forEach((name, index) => {
    actors[name] = signers[index];
  });
  return actors;
}

async function readBalances(token, actors, actorNames) {
  const balances = {};
  for (const name of actorNames) {
    balances[name] = str(await token.balanceOf(actors[name].address));
  }
  return balances;
}

async function mineBlocks(count) {
  for (let i = 0; i < count; i += 1) {
    await ethers.provider.send("evm_mine", []);
  }
}

async function advanceTime(seconds) {
  await ethers.provider.send("evm_increaseTime", [seconds]);
  await ethers.provider.send("evm_mine", []);
}

async function snapshotStep(step, context) {
  const proposal = context.proposalId ? await context.governor.getProposal(context.proposalId) : null;
  return {
    step_id: step.step_id,
    action: step.action,
    pair: {
      reserve0: str(await context.pair.reserve0()),
      reserve1: str(await context.pair.reserve1()),
      fee_bps: Number(await context.pair.feeBps())
    },
    staking: {
      total_staked: str(await context.staking.totalStaked()),
      total_funded: str(await context.staking.totalFunded()),
      total_claimed: str(await context.staking.totalClaimed()),
      reward_rate: str(await context.staking.rewardRate()),
      rewards_duration_seconds: Number(await context.staking.rewardsDuration()),
      period_finish: Number(await context.staking.periodFinish())
    },
    governance: {
      proposal_id: context.proposalId ? String(context.proposalId) : null,
      proposal_status: proposal
        ? {
            snapshot_block: Number(proposal.snapshotBlock),
            deadline_block: Number(proposal.deadlineBlock),
            eta: Number(proposal.eta),
            for_votes: str(proposal.forVotes),
            against_votes: str(proposal.againstVotes),
            queued: proposal.queued,
            executed: proposal.executed
          }
        : null
    }
  };
}

function buildInvariants(report, launchPlan) {
  const totalFunded = BigInt(report.reward_program.total_funded);
  const totalClaimed = BigInt(report.reward_program.total_claimed);
  const expectedFee = Number(launchPlan.pair.fee_bps_after_governance);
  const actualFee = Number(report.pair.fee_bps);
  const proposal = report.governance_token.proposal_status;

  return [
    {
      name: "claimed_within_funded",
      status: totalClaimed <= totalFunded ? "pass" : "fail",
      observed_value: `${totalClaimed}/${totalFunded}`
    },
    {
      name: "governance_fee_applied",
      status: actualFee === expectedFee ? "pass" : "fail",
      observed_value: String(actualFee)
    },
    {
      name: "proposal_executed",
      status: proposal && proposal.executed ? "pass" : "fail",
      observed_value: proposal ? String(proposal.executed) : "false"
    }
  ];
}

async function main() {
  const tokenCatalog = readJson("token_catalog.json");
  const launchPlan = readYaml("launch_plan.yaml");
  const rewardProgramRows = readCsv("reward_program.csv");
  const replaySpec = readJson("scenario_replay.json");
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const signers = await ethers.getSigners();
  const actorNames = getActorNames(launchPlan, replaySpec);
  const actors = buildActors(signers, actorNames);
  const deployer = actors.deployer ?? signers[0];

  const MintableERC20 = await ethers.getContractFactory("MintableERC20");
  const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
  const SimplePair = await ethers.getContractFactory("SimplePair");
  const LaunchStaking = await ethers.getContractFactory("LaunchStaking");
  const LaunchGovernor = await ethers.getContractFactory("LaunchGovernor");

  const base = await MintableERC20.deploy(tokenCatalog.base.name, tokenCatalog.base.symbol, tokenCatalog.base.decimals);
  await base.waitForDeployment();
  const quote = await MintableERC20.deploy(tokenCatalog.quote.name, tokenCatalog.quote.symbol, tokenCatalog.quote.decimals);
  await quote.waitForDeployment();

  const allocations = launchPlan.governance_token.initial_allocations;
  const recipients = actorNames.map((name) => actors[name].address);
  const govAllocations = actorNames.map((name) => allocations[name]);

  const governanceToken = await GovernanceToken.deploy(
    tokenCatalog.governance.name,
    tokenCatalog.governance.symbol,
    tokenCatalog.governance.decimals,
    launchPlan.governance_token.cap,
    recipients,
    govAllocations
  );
  await governanceToken.waitForDeployment();

  for (const actorName of actorNames) {
    await base.mint(actors[actorName].address, launchPlan.assets.base.initial_allocations[actorName]);
    await quote.mint(actors[actorName].address, launchPlan.assets.quote.initial_allocations[actorName]);
  }

  const pair = await SimplePair.deploy(await base.getAddress(), await quote.getAddress(), launchPlan.pair.fee_bps);
  await pair.waitForDeployment();

  const staking = await LaunchStaking.deploy(
    await pair.getAddress(),
    await governanceToken.getAddress(),
    deployer.address,
    launchPlan.rewards.duration_seconds
  );
  await staking.waitForDeployment();

  const governor = await LaunchGovernor.deploy(
    await governanceToken.getAddress(),
    launchPlan.governance.proposal_threshold,
    launchPlan.governance.quorum_votes,
    launchPlan.governance.voting_delay_blocks,
    launchPlan.governance.voting_period_blocks,
    launchPlan.governance.timelock_delay_seconds
  );
  await governor.waitForDeployment();

  await pair.transferOwnership(await governor.getAddress());
  await staking.transferOwnership(await governor.getAddress());

  for (const actorName of actorNames) {
    const actor = actors[actorName];
    await base.connect(actor).approve(await pair.getAddress(), ethers.MaxUint256);
    await quote.connect(actor).approve(await pair.getAddress(), ethers.MaxUint256);
    await pair.connect(actor).approve(await staking.getAddress(), ethers.MaxUint256);
  }
  await governanceToken.connect(deployer).approve(await staking.getAddress(), ethers.MaxUint256);

  const rewardByEpoch = {};
  for (const row of rewardProgramRows) {
    rewardByEpoch[row.epoch_id] = row;
  }

  const context = { pair, staking, governor, proposalId: null };
  const scenarioResults = [];

  for (const step of replaySpec.steps) {
    if (step.action === "seed_pair" || step.action === "add_liquidity") {
      await pair.connect(actors[step.actor]).addLiquidity(step.amount0, step.amount1);
    } else if (step.action === "remove_liquidity") {
      const actor = actors[step.actor];
      const balance = await pair.balanceOf(actor.address);
      const amount = getShareAmount(balance, step.share_bps);
      await pair.connect(actor).removeLiquidity(amount);
    } else if (step.action === "fund_rewards") {
      const epoch = rewardByEpoch[step.epoch_id];
      const amount = step.amount || (epoch ? epoch.funding_amount : "0");
      await staking.connect(actors[step.actor]).fundProgram(amount);
    } else if (step.action === "stake_lp") {
      const actor = actors[step.actor];
      const balance = await pair.balanceOf(actor.address);
      const amount = getShareAmount(balance, step.share_bps);
      await staking.connect(actor).stake(amount);
    } else if (step.action === "swap_exact_in") {
      const actor = actors[step.actor];
      const tokenIn = step.token_in === "base" ? await base.getAddress() : await quote.getAddress();
      await pair.connect(actor).swap(tokenIn, step.amount_in, 0);
    } else if (step.action === "advance_time") {
      await advanceTime(step.seconds);
    } else if (step.action === "claim_rewards") {
      await staking.connect(actors[step.actor]).getReward();
    } else if (step.action === "delegate_votes") {
      await governanceToken.connect(actors[step.actor]).delegate(actors[step.delegatee].address);
    } else if (step.action === "transfer_gov") {
      await governanceToken.connect(actors[step.actor]).transfer(actors[step.to].address, step.amount);
    } else if (step.action === "propose_fee_update") {
      const fee = step.new_fee_bps ?? launchPlan.pair.fee_bps_after_governance;
      const calldata = pair.interface.encodeFunctionData("setFeeBps", [fee]);
      await governor.connect(actors[step.actor]).propose([await pair.getAddress()], [0], [calldata]);
      context.proposalId = Number(await governor.proposalCount());
    } else if (step.action === "propose_rewards_duration_update") {
      const calldata = staking.interface.encodeFunctionData("setRewardsDuration", [step.new_duration_seconds]);
      await governor.connect(actors[step.actor]).propose([await staking.getAddress()], [0], [calldata]);
      context.proposalId = Number(await governor.proposalCount());
    } else if (step.action === "advance_blocks") {
      await mineBlocks(step.count);
    } else if (step.action === "vote") {
      await governor.connect(actors[step.actor]).castVote(context.proposalId, asBool(step.support));
    } else if (step.action === "queue") {
      await governor.connect(actors[step.actor]).queue(context.proposalId);
    } else if (step.action === "execute") {
      await governor.connect(actors[step.actor]).execute(context.proposalId);
    } else if (step.action === "withdraw") {
      const actor = actors[step.actor];
      const staked = await staking.balances(actor.address);
      const amount = getShareAmount(staked, step.share_bps);
      await staking.connect(actor).withdraw(amount);
    } else if (step.action === "exit") {
      await staking.connect(actors[step.actor]).exit();
    } else {
      throw new Error(`Unsupported action ${step.action}`);
    }

    scenarioResults.push(await snapshotStep(step, context));
  }

  const proposal = context.proposalId ? await governor.getProposal(context.proposalId) : null;
  const lpBalances = await readBalances(pair, actors, actorNames);
  const currentVotes = {};
  for (const actorName of actorNames) {
    currentVotes[actorName] = str(await governanceToken.getVotes(actors[actorName].address));
  }
  const stakerBalances = {};
  for (const actorName of actorNames) {
    stakerBalances[actorName] = str(await staking.balances(actors[actorName].address));
  }
  const report = {
    pair: {
      token0: tokenCatalog.base.symbol,
      token1: tokenCatalog.quote.symbol,
      fee_bps: Number(await pair.feeBps()),
      reserve0: str(await pair.reserve0()),
      reserve1: str(await pair.reserve1()),
      total_lp_supply: str(await pair.totalSupply()),
      lp_balances: lpBalances,
    },
    governance_token: {
      name: await governanceToken.name(),
      symbol: await governanceToken.symbol(),
      decimals: Number(await governanceToken.decimals()),
      cap: str(await governanceToken.cap()),
      total_supply: str(await governanceToken.totalSupply()),
      proposal_count: Number(await governor.proposalCount()),
      current_votes: currentVotes,
      proposal_status: proposal
        ? {
            snapshot_block: Number(proposal.snapshotBlock),
            deadline_block: Number(proposal.deadlineBlock),
            eta: Number(proposal.eta),
            for_votes: str(proposal.forVotes),
            against_votes: str(proposal.againstVotes),
            queued: proposal.queued,
            executed: proposal.executed
          }
        : null
    },
    reward_program: {
      total_funded: str(await staking.totalFunded()),
      total_claimed: str(await staking.totalClaimed()),
      reward_rate: str(await staking.rewardRate()),
      rewards_duration_seconds: Number(await staking.rewardsDuration()),
      period_finish: Number(await staking.periodFinish()),
      total_staked: str(await staking.totalStaked()),
      staker_balances: stakerBalances,
    },
    scenario_results: scenarioResults
  };

  report.invariant_checks = buildInvariants(report, launchPlan);
  fs.writeFileSync(path.join(OUT_DIR, "launch_report.json"), `${JSON.stringify(report, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
