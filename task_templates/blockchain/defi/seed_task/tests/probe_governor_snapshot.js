const path = require("path");

const ROOT = process.env.TASK_WORKSPACE_ROOT || process.env.TASK_WORKSPACE_DIR || "/root/workspace";
const hre = global.hre || require(path.join(ROOT, "node_modules", "hardhat"));

const { ethers } = hre;

function str(value) {
  return value.toString();
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

async function main() {
  const [deployer, alice, bob] = await ethers.getSigners();

  const MintableERC20 = await ethers.getContractFactory("MintableERC20");
  const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
  const SimplePair = await ethers.getContractFactory("SimplePair");
  const LaunchGovernor = await ethers.getContractFactory("LaunchGovernor");

  const token0 = await MintableERC20.deploy("Vote Dollar", "VDL", 18);
  await token0.waitForDeployment();
  const token1 = await MintableERC20.deploy("Vote Ether", "VET", 18);
  await token1.waitForDeployment();
  const pair = await SimplePair.deploy(await token0.getAddress(), await token1.getAddress(), 30);
  await pair.waitForDeployment();

  const cap = ethers.parseEther("1000000");
  const governanceToken = await GovernanceToken.deploy(
    "VoteGov",
    "VGOV",
    18,
    cap,
    [deployer.address, alice.address, bob.address],
    [0, ethers.parseEther("400000"), ethers.parseEther("100000")]
  );
  await governanceToken.waitForDeployment();

  const governor = await LaunchGovernor.deploy(
    await governanceToken.getAddress(),
    ethers.parseEther("150000"),
    ethers.parseEther("250000"),
    1,
    6,
    3600
  );
  await governor.waitForDeployment();
  await pair.transferOwnership(await governor.getAddress());

  await governanceToken.connect(alice).delegate(alice.address);
  await mineBlocks(1);

  const calldata = pair.interface.encodeFunctionData("setFeeBps", [20]);
  await governor.connect(alice).propose([await pair.getAddress()], [0], [calldata]);
  const proposalId = await governor.proposalCount();
  const proposalBeforeVotes = await governor.getProposal(proposalId);

  await mineBlocks(1);
  await governanceToken.connect(alice).transfer(bob.address, ethers.parseEther("100000"));
  await governanceToken.connect(bob).delegate(bob.address);

  let bobVoteRejected = false;
  try {
    await governor.connect(bob).castVote(proposalId, true);
  } catch (error) {
    bobVoteRejected = true;
  }

  await governor.connect(alice).castVote(proposalId, true);
  const proposalAfterAliceVote = await governor.getProposal(proposalId);

  await mineBlocks(7);
  await governor.connect(alice).queue(proposalId);
  await advanceTime(3600);
  await governor.connect(alice).execute(proposalId);

  console.log(
    JSON.stringify(
      {
        proposal_id: Number(proposalId),
        snapshot_block: Number(proposalBeforeVotes.snapshotBlock),
        deadline_block: Number(proposalBeforeVotes.deadlineBlock),
        bob_vote_rejected: bobVoteRejected,
        for_votes_after_alice: str(proposalAfterAliceVote.forVotes),
        against_votes_after_alice: str(proposalAfterAliceVote.againstVotes),
        final_fee_bps: Number(await pair.feeBps()),
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
