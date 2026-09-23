const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");
const hre = require("hardhat");

const { ethers } = hre;

const ROOT = process.env.TASK_WORKSPACE_DIR || path.resolve(__dirname, "..");
const SPEC_DIR = path.join(ROOT, "spec");
const OUT_DIR = process.env.TASK_OUTPUT_DIR || path.join(ROOT, "out");

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
    const item = {};
    headers.forEach((header, index) => {
      item[header] = values[index];
    });
    return item;
  });
}

function str(value) {
  return value.toString();
}

function bn(value) {
  return BigInt(value);
}

async function mineBlocks(count) {
  for (let index = 0; index < count; index += 1) {
    await ethers.provider.send("evm_mine", []);
  }
}

async function advanceTime(seconds) {
  await ethers.provider.send("evm_increaseTime", [seconds]);
  await ethers.provider.send("evm_mine", []);
}

async function snapshotStep(step, context) {
  const latestBlock = await ethers.provider.getBlock("latest");
  const proposalInfo = context.currentProposalId ? await context.governor.getProposal(context.currentProposalId) : null;
  const actorSnapshots = {};

  for (const actorName of Object.keys(context.actors)) {
    actorSnapshots[actorName] = {
      base_balance: str(await context.token0.balanceOf(context.actors[actorName].address)),
      quote_balance: str(await context.token1.balanceOf(context.actors[actorName].address)),
      lp_balance: str(await context.pair.balanceOf(context.actors[actorName].address)),
      staked_lp: str(await context.staking.balances(context.actors[actorName].address)),
      reward_earned: str(await context.staking.earned(context.actors[actorName].address)),
      gov_balance: str(await context.govToken.balanceOf(context.actors[actorName].address)),
      votes: str(await context.govToken.getVotes(context.actors[actorName].address))
    };
  }

  return {
    step_id: step.step_id,
    action: step.action,
    block_number: Number(latestBlock.number),
    timestamp: Number(latestBlock.timestamp),
    pair: {
      reserve0: str(await context.pair.reserve0()),
      reserve1: str(await context.pair.reserve1()),
      fee_bps: Number(await context.pair.feeBps()),
      total_lp_supply: str(await context.pair.totalSupply())
    },
    staking: {
      total_staked: str(await context.staking.totalStaked()),
      total_funded: str(await context.staking.totalFunded()),
      total_claimed: str(await context.staking.totalClaimed()),
      reward_rate: str(await context.staking.rewardRate()),
      reward_per_token_stored: str(await context.staking.rewardPerTokenStored()),
      rewards_duration_seconds: Number(await context.staking.rewardsDuration()),
      period_finish: Number(await context.staking.periodFinish())
    },
    governance: {
      proposal_id: context.currentProposalId ? String(context.currentProposalId) : null,
      proposal: proposalInfo
        ? {
            snapshot_block: Number(proposalInfo.snapshotBlock),
            deadline_block: Number(proposalInfo.deadlineBlock),
            eta: Number(proposalInfo.eta),
            for_votes: str(proposalInfo.forVotes),
            against_votes: str(proposalInfo.againstVotes),
            queued: proposalInfo.queued,
            executed: proposalInfo.executed
          }
        : null
    },
    actors: actorSnapshots
  };
}

async function main() {
  const tokenCatalog = readJson("token_catalog.json");
  const launchPlan = readYaml("launch_plan.yaml");
  const replaySpec = readJson("scenario_replay.json");
  const rewardProgram = readCsv("reward_program.csv");
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const signers = await ethers.getSigners();
  const actors = {
    deployer: signers[0],
    alice: signers[1],
    bob: signers[2],
    carol: signers[3]
  };
  const epochs = Object.fromEntries(rewardProgram.map((row) => [row.epoch_id, row]));

  const MintableERC20 = await ethers.getContractFactory("MintableERC20");
  const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
  const SimplePair = await ethers.getContractFactory("SimplePair");
  const LaunchStaking = await ethers.getContractFactory("LaunchStaking");
  const LaunchGovernor = await ethers.getContractFactory("LaunchGovernor");

  const token0Meta = tokenCatalog.base;
  const token1Meta = tokenCatalog.quote;
  const token0 = await MintableERC20.deploy(token0Meta.name, token0Meta.symbol, token0Meta.decimals);
  await token0.waitForDeployment();
  const token1 = await MintableERC20.deploy(token1Meta.name, token1Meta.symbol, token1Meta.decimals);
  await token1.waitForDeployment();

  const govToken = await GovernanceToken.deploy(
    tokenCatalog.governance.name,
    tokenCatalog.governance.symbol,
    tokenCatalog.governance.decimals,
    launchPlan.governance_token.cap,
    [actors.deployer.address, actors.alice.address, actors.bob.address, actors.carol.address],
    [
      launchPlan.governance_token.initial_allocations.deployer,
      launchPlan.governance_token.initial_allocations.alice,
      launchPlan.governance_token.initial_allocations.bob,
      launchPlan.governance_token.initial_allocations.carol
    ]
  );
  await govToken.waitForDeployment();

  for (const actorName of Object.keys(actors)) {
    await token0.mint(actors[actorName].address, launchPlan.assets.base.initial_allocations[actorName]);
    await token1.mint(actors[actorName].address, launchPlan.assets.quote.initial_allocations[actorName]);
  }

  const pair = await SimplePair.deploy(await token0.getAddress(), await token1.getAddress(), launchPlan.pair.fee_bps);
  await pair.waitForDeployment();

  const staking = await LaunchStaking.deploy(
    await pair.getAddress(),
    await govToken.getAddress(),
    actors.deployer.address,
    launchPlan.rewards.duration_seconds
  );
  await staking.waitForDeployment();

  const governor = await LaunchGovernor.deploy(
    await govToken.getAddress(),
    launchPlan.governance.proposal_threshold,
    launchPlan.governance.quorum_votes,
    launchPlan.governance.voting_delay_blocks,
    launchPlan.governance.voting_period_blocks,
    launchPlan.governance.timelock_delay_seconds
  );
  await governor.waitForDeployment();

  await pair.transferOwnership(await governor.getAddress());
  await staking.transferOwnership(await governor.getAddress());

  for (const actorName of Object.keys(actors)) {
    await token0.connect(actors[actorName]).approve(await pair.getAddress(), ethers.MaxUint256);
    await token1.connect(actors[actorName]).approve(await pair.getAddress(), ethers.MaxUint256);
    await pair.connect(actors[actorName]).approve(await staking.getAddress(), ethers.MaxUint256);
  }
  await govToken.connect(actors.deployer).approve(await staking.getAddress(), ethers.MaxUint256);

  const context = {
    actors,
    currentProposalId: null,
    govToken,
    governor,
    pair,
    staking,
    token0,
    token1
  };
  const scenarioResults = [];

  for (const step of replaySpec.steps) {
    if (step.action === "seed_pair" || step.action === "add_liquidity") {
      await pair.connect(actors[step.actor]).addLiquidity(step.amount0, step.amount1);
    } else if (step.action === "fund_rewards") {
      const epoch = epochs[step.epoch_id];
      if (!epoch) {
        throw new Error(`Missing reward epoch ${step.epoch_id}`);
      }
      if (epoch.funding_amount !== step.amount) {
        throw new Error(`Funding mismatch for ${step.epoch_id}`);
      }
      await staking.connect(actors[step.actor]).fundProgram(step.amount);
    } else if (step.action === "stake_lp") {
      const lpBalance = await pair.balanceOf(actors[step.actor].address);
      const amount = (lpBalance * BigInt(step.share_bps)) / 10000n;
      await staking.connect(actors[step.actor]).stake(amount);
    } else if (step.action === "swap_exact_in") {
      const tokenIn = step.token_in === "base" ? await token0.getAddress() : await token1.getAddress();
      await pair.connect(actors[step.actor]).swap(tokenIn, step.amount_in, 0);
    } else if (step.action === "advance_time") {
      await advanceTime(step.seconds);
    } else if (step.action === "claim_rewards") {
      await staking.connect(actors[step.actor]).getReward();
    } else if (step.action === "delegate_votes") {
      await govToken.connect(actors[step.actor]).delegate(actors[step.delegatee].address);
    } else if (step.action === "transfer_gov") {
      await govToken.connect(actors[step.actor]).transfer(actors[step.to].address, step.amount);
    } else if (step.action === "propose_fee_update") {
      const calldata = pair.interface.encodeFunctionData("setFeeBps", [step.new_fee_bps]);
      await governor.connect(actors[step.actor]).propose([await pair.getAddress()], [0], [calldata]);
      context.currentProposalId = Number(await governor.proposalCount());
    } else if (step.action === "advance_blocks") {
      await mineBlocks(step.count);
    } else if (step.action === "vote") {
      await governor.connect(actors[step.actor]).castVote(context.currentProposalId, step.support === "for");
    } else if (step.action === "queue") {
      await governor.connect(actors[step.actor]).queue(context.currentProposalId);
    } else if (step.action === "execute") {
      await governor.connect(actors[step.actor]).execute(context.currentProposalId);
    } else if (step.action === "withdraw") {
      const stakedBalance = await staking.balances(actors[step.actor].address);
      const amount = (stakedBalance * BigInt(step.share_bps)) / 10000n;
      await staking.connect(actors[step.actor]).withdraw(amount);
    } else if (step.action === "exit") {
      await staking.connect(actors[step.actor]).exit();
    } else {
      throw new Error(`Unsupported action ${step.action}`);
    }

    scenarioResults.push(await snapshotStep(step, context));
  }

  const proposal = context.currentProposalId ? await governor.getProposal(context.currentProposalId) : null;
  const totalFunded = await staking.totalFunded();
  const totalClaimed = await staking.totalClaimed();
  const reserve0 = await pair.reserve0();
  const reserve1 = await pair.reserve1();
  const finalFeeBps = await pair.feeBps();

  const payload = {
    pair: {
      token0: token0Meta.symbol,
      token1: token1Meta.symbol,
      fee_bps: Number(finalFeeBps),
      reserve0: str(reserve0),
      reserve1: str(reserve1),
      total_lp_supply: str(await pair.totalSupply()),
      lp_balances: {
        alice: str(await pair.balanceOf(actors.alice.address)),
        bob: str(await pair.balanceOf(actors.bob.address))
      }
    },
    governance_token: {
      name: await govToken.name(),
      symbol: await govToken.symbol(),
      decimals: Number(await govToken.decimals()),
      cap: str(await govToken.cap()),
      total_supply: str(await govToken.totalSupply()),
      proposal_count: Number(await governor.proposalCount()),
      current_votes: {
        alice: str(await govToken.getVotes(actors.alice.address)),
        bob: str(await govToken.getVotes(actors.bob.address)),
        carol: str(await govToken.getVotes(actors.carol.address))
      },
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
      total_funded: str(totalFunded),
      total_claimed: str(totalClaimed),
      reward_rate: str(await staking.rewardRate()),
      rewards_duration_seconds: Number(await staking.rewardsDuration()),
      period_finish: Number(await staking.periodFinish()),
      total_staked: str(await staking.totalStaked()),
      epochs: rewardProgram.map((row) => ({
        epoch_id: row.epoch_id,
        start_offset_seconds: Number(row.start_offset_seconds),
        funding_amount: row.funding_amount,
        duration_seconds: Number(row.duration_seconds)
      })),
      staker_balances: {
        alice: str(await staking.balances(actors.alice.address)),
        bob: str(await staking.balances(actors.bob.address))
      }
    },
    contracts: {
      token0: await token0.getAddress(),
      token1: await token1.getAddress(),
      governance_token: await govToken.getAddress(),
      pair: await pair.getAddress(),
      staking: await staking.getAddress(),
      governor: await governor.getAddress()
    },
    actors: {
      deployer: actors.deployer.address,
      alice: actors.alice.address,
      bob: actors.bob.address,
      carol: actors.carol.address
    },
    scenario_results: scenarioResults,
    invariant_checks: [
      {
        name: "claims_within_funding",
        status: bn(totalClaimed) <= bn(totalFunded) ? "pass" : "fail",
        observed_value: JSON.stringify({
          total_claimed: str(totalClaimed),
          total_funded: str(totalFunded)
        })
      },
      {
        name: "fee_update_executed",
        status: Number(finalFeeBps) === launchPlan.pair.fee_bps_after_governance ? "pass" : "fail",
        observed_value: str(finalFeeBps)
      },
      {
        name: "proposal_executed",
        status: proposal && proposal.executed ? "pass" : "fail",
        observed_value: proposal
          ? JSON.stringify({
              for_votes: str(proposal.forVotes),
              against_votes: str(proposal.againstVotes),
              queued: proposal.queued,
              executed: proposal.executed
            })
          : "null"
      },
      {
        name: "pool_nonempty",
        status: bn(reserve0) > 0n && bn(reserve1) > 0n ? "pass" : "fail",
        observed_value: JSON.stringify({
          reserve0: str(reserve0),
          reserve1: str(reserve1)
        })
      }
    ]
  };

  fs.writeFileSync(path.join(OUT_DIR, "launch_report.json"), JSON.stringify(payload, null, 2) + "\n");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
