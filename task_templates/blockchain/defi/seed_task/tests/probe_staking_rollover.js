const path = require("path");

const ROOT = process.env.TASK_WORKSPACE_ROOT || process.env.TASK_WORKSPACE_DIR || "/root/workspace";
const hre = global.hre || require(path.join(ROOT, "node_modules", "hardhat"));

const { ethers } = hre;

function str(value) {
  return value.toString();
}

function bn(value) {
  return BigInt(value.toString());
}

async function advanceTime(seconds) {
  await ethers.provider.send("evm_increaseTime", [seconds]);
  await ethers.provider.send("evm_mine", []);
}

async function main() {
  const [deployer, alice, bob] = await ethers.getSigners();

  const MintableERC20 = await ethers.getContractFactory("MintableERC20");
  const LaunchStaking = await ethers.getContractFactory("LaunchStaking");

  const stakingToken = await MintableERC20.deploy("Probe LP", "PLP", 18);
  await stakingToken.waitForDeployment();
  const rewardsToken = await MintableERC20.deploy("Probe Reward", "PRW", 18);
  await rewardsToken.waitForDeployment();

  await stakingToken.mint(alice.address, ethers.parseEther("300"));
  await stakingToken.mint(bob.address, ethers.parseEther("200"));
  await rewardsToken.mint(deployer.address, ethers.parseEther("5000"));

  const staking = await LaunchStaking.deploy(
    await stakingToken.getAddress(),
    await rewardsToken.getAddress(),
    deployer.address,
    1000
  );
  await staking.waitForDeployment();

  await stakingToken.connect(alice).approve(await staking.getAddress(), ethers.MaxUint256);
  await stakingToken.connect(bob).approve(await staking.getAddress(), ethers.MaxUint256);
  await rewardsToken.connect(deployer).approve(await staking.getAddress(), ethers.MaxUint256);

  await staking.connect(alice).stake(ethers.parseEther("100"));
  await staking.connect(deployer).fundProgram(ethers.parseEther("1000"));

  const firstRate = await staking.rewardRate();
  const firstFinish = await staking.periodFinish();
  await advanceTime(200);

  const secondFundAmount = ethers.parseEther("500");
  await staking.connect(bob).stake(ethers.parseEther("50"));
  const secondFundTx = await staking.connect(deployer).fundProgram(secondFundAmount);
  const secondFundReceipt = await secondFundTx.wait();
  const secondFundBlock = await ethers.provider.getBlock(secondFundReceipt.blockNumber);
  const remaining = bn(firstFinish) - BigInt(secondFundBlock.timestamp);
  const expectedSecondRate = (bn(secondFundAmount) + (remaining * bn(firstRate))) / 1000n;
  const actualSecondRate = await staking.rewardRate();

  await advanceTime(400);
  const earnedAliceBeforeClaim = await staking.earned(alice.address);
  await staking.connect(alice).getReward();
  const aliceRewardBalance = await rewardsToken.balanceOf(alice.address);

  await advanceTime(200);
  await staking.connect(bob).exit();

  console.log(
    JSON.stringify(
      {
        first_rate: str(firstRate),
        expected_second_rate: str(expectedSecondRate),
        actual_second_rate: str(actualSecondRate),
        earned_alice_before_claim: str(earnedAliceBeforeClaim),
        alice_reward_balance: str(aliceRewardBalance),
        total_funded: str(await staking.totalFunded()),
        total_claimed: str(await staking.totalClaimed()),
        remaining_bob_stake: str(await staking.balances(bob.address)),
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
