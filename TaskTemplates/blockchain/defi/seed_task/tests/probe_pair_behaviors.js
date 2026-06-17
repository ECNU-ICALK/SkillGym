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

async function main() {
  const [deployer, alice, bob] = await ethers.getSigners();

  const MintableERC20 = await ethers.getContractFactory("MintableERC20");
  const SimplePair = await ethers.getContractFactory("SimplePair");

  const token0 = await MintableERC20.deploy("Probe Dollar", "PUSD", 18);
  await token0.waitForDeployment();
  const token1 = await MintableERC20.deploy("Probe Ether", "PETH", 18);
  await token1.waitForDeployment();

  const pair = await SimplePair.deploy(await token0.getAddress(), await token1.getAddress(), 25);
  await pair.waitForDeployment();

  const aliceSeed0 = ethers.parseEther("500");
  const aliceSeed1 = ethers.parseEther("250");
  const bobSeed0 = ethers.parseEther("200");
  const bobSeed1 = ethers.parseEther("100");
  const bobSwapIn = ethers.parseEther("10");

  await token0.mint(alice.address, aliceSeed0);
  await token1.mint(alice.address, aliceSeed1);
  await token0.mint(bob.address, bobSeed0);
  await token1.mint(bob.address, bobSeed1);

  for (const signer of [alice, bob]) {
    await token0.connect(signer).approve(await pair.getAddress(), ethers.MaxUint256);
    await token1.connect(signer).approve(await pair.getAddress(), ethers.MaxUint256);
  }

  await pair.connect(alice).addLiquidity(ethers.parseEther("400"), ethers.parseEther("200"));
  await pair.connect(bob).addLiquidity(ethers.parseEther("100"), ethers.parseEther("50"));

  const bobLp = await pair.balanceOf(bob.address);
  const bobBaseBeforeRemove = await token0.balanceOf(bob.address);
  const bobQuoteBeforeRemove = await token1.balanceOf(bob.address);
  await pair.connect(bob).removeLiquidity(bobLp);
  const bobBaseAfterRemove = await token0.balanceOf(bob.address);
  const bobQuoteAfterRemove = await token1.balanceOf(bob.address);

  const bobRemoved0 = bn(bobBaseAfterRemove) - bn(bobBaseBeforeRemove);
  const bobRemoved1 = bn(bobQuoteAfterRemove) - bn(bobQuoteBeforeRemove);
  const reservesAfterRemove0 = await pair.reserve0();
  const reservesAfterRemove1 = await pair.reserve1();

  await pair.connect(bob).addLiquidity(ethers.parseEther("100"), ethers.parseEther("50"));

  const reserve0BeforeSwap = await pair.reserve0();
  const reserve1BeforeSwap = await pair.reserve1();
  const bobQuoteBeforeSwap = await token1.balanceOf(bob.address);
  const kBeforeSwap = bn(reserve0BeforeSwap) * bn(reserve1BeforeSwap);

  await pair.connect(bob).swap(await token0.getAddress(), bobSwapIn, 0);

  const reserve0AfterSwap = await pair.reserve0();
  const reserve1AfterSwap = await pair.reserve1();
  const bobQuoteAfterSwap = await token1.balanceOf(bob.address);
  const kAfterSwap = bn(reserve0AfterSwap) * bn(reserve1AfterSwap);

  const amountInWithFee = (bn(bobSwapIn) * 9975n) / 10000n;
  const expectedOut = (bn(reserve1BeforeSwap) * amountInWithFee) / (bn(reserve0BeforeSwap) + amountInWithFee);
  const actualOut = bn(bobQuoteAfterSwap) - bn(bobQuoteBeforeSwap);

  console.log(
    JSON.stringify(
      {
        removed_amount0: str(bobRemoved0),
        removed_amount1: str(bobRemoved1),
        reserves_after_remove0: str(reservesAfterRemove0),
        reserves_after_remove1: str(reservesAfterRemove1),
        expected_swap_out: str(expectedOut),
        actual_swap_out: str(actualOut),
        k_before_swap: str(kBeforeSwap),
        k_after_swap: str(kAfterSwap),
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
