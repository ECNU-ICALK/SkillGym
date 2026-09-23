const path = require("path");

const ROOT = process.env.TASK_WORKSPACE_ROOT || process.env.TASK_WORKSPACE_DIR || "/root/workspace";
const hre = require(path.join(ROOT, "node_modules", "hardhat"));

const { ethers } = hre;

function str(value) {
  return value.toString();
}

async function main() {
  const [, alice, donor] = await ethers.getSigners();

  const MintableERC20 = await ethers.getContractFactory("MintableERC20");
  const SimplePair = await ethers.getContractFactory("SimplePair");

  const token0 = await MintableERC20.deploy("Sync Base", "SBASE", 18);
  await token0.waitForDeployment();
  const token1 = await MintableERC20.deploy("Sync Quote", "SQUOTE", 18);
  await token1.waitForDeployment();
  const pair = await SimplePair.deploy(await token0.getAddress(), await token1.getAddress(), 30);
  await pair.waitForDeployment();

  await token0.mint(alice.address, ethers.parseEther("500"));
  await token1.mint(alice.address, ethers.parseEther("250"));
  await token0.mint(donor.address, ethers.parseEther("50"));
  await token1.mint(donor.address, ethers.parseEther("25"));

  await token0.connect(alice).approve(await pair.getAddress(), ethers.MaxUint256);
  await token1.connect(alice).approve(await pair.getAddress(), ethers.MaxUint256);

  await pair.connect(alice).addLiquidity(ethers.parseEther("500"), ethers.parseEther("250"));
  const removeShares = (await pair.balanceOf(alice.address)) / 2n;

  await token0.connect(donor).transfer(await pair.getAddress(), ethers.parseEther("50"));
  await token1.connect(donor).transfer(await pair.getAddress(), ethers.parseEther("25"));

  await pair.connect(alice).removeLiquidity(removeShares);

  const reserve0 = await pair.reserve0();
  const reserve1 = await pair.reserve1();
  const actualBalance0 = await token0.balanceOf(await pair.getAddress());
  const actualBalance1 = await token1.balanceOf(await pair.getAddress());

  console.log(
    JSON.stringify(
      {
        reserve0: str(reserve0),
        reserve1: str(reserve1),
        actual_balance0: str(actualBalance0),
        actual_balance1: str(actualBalance1),
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
