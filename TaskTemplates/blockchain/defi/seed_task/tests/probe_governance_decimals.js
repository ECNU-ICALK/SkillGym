#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const hre = global.hre;

if (!hre) {
  throw new Error("Hardhat runtime environment is not available");
}

const { ethers } = hre;

const ROOT = process.env.TASK_WORKSPACE_DIR || process.env.TASK_WORKSPACE_ROOT || "/root/workspace";
const SPEC_DIR = path.join(ROOT, "spec");
const yaml = require(path.join(ROOT, "node_modules", "js-yaml"));

function readYaml(name) {
  return yaml.load(fs.readFileSync(path.join(SPEC_DIR, name), "utf8"));
}

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(SPEC_DIR, name), "utf8"));
}

async function main() {
  const tokenCatalog = readJson("token_catalog.json");
  const launchPlan = readYaml("launch_plan.yaml");
  const [deployer, alice, bob, carol] = await ethers.getSigners();
  const GovernanceToken = await ethers.getContractFactory("GovernanceToken");

  const governanceToken = await GovernanceToken.deploy(
    tokenCatalog.governance.name,
    tokenCatalog.governance.symbol,
    tokenCatalog.governance.decimals,
    launchPlan.governance_token.cap,
    [deployer.address, alice.address, bob.address, carol.address],
    [
      launchPlan.governance_token.initial_allocations.deployer,
      launchPlan.governance_token.initial_allocations.alice,
      launchPlan.governance_token.initial_allocations.bob,
      launchPlan.governance_token.initial_allocations.carol,
    ]
  );
  await governanceToken.waitForDeployment();

  process.stdout.write(
    `${JSON.stringify({
      name: await governanceToken.name(),
      symbol: await governanceToken.symbol(),
      decimals: Number(await governanceToken.decimals()),
    })}\n`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
