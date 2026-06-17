You are completing the local Hardhat workspace in `/root/workspace/` for a governance-enabled liquidity mining launch. The workspace must compile, deploy on the bundled local chain, replay the provided launch scenarios, and produce an auditable protocol report.

Input data is in `/root/workspace/spec/`:
- `launch_plan.yaml`: protocol parameters, token pair settings, fee units, governance settings, and initial allocations.
- `token_catalog.json`: token metadata and decimals for the launch assets.
- `reward_program.csv`: LP reward emission schedule for the launch campaign.
- `scenario_replay.json`: deterministic launch sequence covering liquidity actions, swaps, staking actions, claims, delegation, proposal voting, queueing, and execution.
- `reference/`: reference material for AMM behavior, staking reward accounting, and vote checkpoint semantics.

The provided workspace is in `/root/workspace/`:
- `run_launch.sh`: the unified entrypoint for local build, deployment, scenario replay, and report generation; keep this path and filename
- `contracts/`
- `scripts/`
- `hardhat.config.js`
- `package.json`

Your task:
1. Complete the Solidity contracts and supporting scripts so that `run_launch.sh` can build the project, deploy the protocol to the local chain, replay the provided scenario, and keep the workflow reproducible from the input files above.
2. Deliver a vote-enabled governance token whose name, symbol, cap, and initial allocations follow `launch_plan.yaml`.
3. Deliver a constant-product AMM for the configured token pair with liquidity minting, liquidity burning, reserve tracking, and exact-input swaps that apply the configured fee.
4. Deliver an LP staking rewards contract that uses `reward_program.csv`, supports stake, withdraw, claim, and exit flows, and keeps reward accounting consistent when new reward funding arrives before the active campaign has ended.
5. Ensure governance voting power follows delegation checkpoints across mint, transfer, and delegate actions in the replay, and ensure approved governance actions can be queued and executed under the timing rules from `launch_plan.yaml`.
6. Build the replay and report flow from the provided inputs instead of assuming a fixed actor list, a fixed proposal target, or a single proposal payload shape. Actor discovery, allocations, and action dispatch must follow the files under `spec/`.
7. A rerun of `run_launch.sh` against the same workspace and the same `spec/` inputs must regenerate the same protocol state and the same report content, aside from timing metadata that naturally changes across executions.
8. Write the final machine-readable report to `/root/workspace/out/launch_report.json`.

Output:
- `/root/workspace/out/launch_report.json`

`/root/workspace/out/launch_report.json` must be valid UTF-8 JSON and include at least these top-level fields:
- `pair`
- `governance_token`
- `reward_program`
- `scenario_results`
- `invariant_checks`

Output requirements:
- All token, reserve, LP-share, reward, and vote quantities must be base-unit decimal strings.
- `scenario_results` must be a JSON array ordered by replay step.
- `invariant_checks` must be a JSON array of objects with:
  - `name`
  - `status`
  - `observed_value`
- Actor-keyed summary objects must cover every actor that appears in the launch allocations or in replay steps and ends the run with LP balance, staked LP balance, or delegated voting power. These summaries may appear under `pair.lp_balances`, `reward_program.staker_balances`, `governance_token.current_votes`, or a separate `actor_summaries` object, as long as the coverage is complete.

Business requirements:
- Token ordering, decimals, fee units, governance settings, and initial allocations must come from the provided inputs.
- Replay support must cover every action type that appears in `scenario_replay.json`, including liquidity removal, governance actions that update pair settings, and governance actions that update reward-program settings when those actions are present in the input.
- LP share minting and redemption must use on-chain integer arithmetic and remain auditable from the replay steps.
- Swap output amounts must keep the constant-product pool state consistent under the configured fee model.
- Reward accrual must be time-based, proportional to staked LP balances, and monotonic across the replay timestamps.
- Claims must stay within funded rewards across the full replay.
- Governance actions executed during the replay must apply the parameter updates referenced by `scenario_replay.json`.

Notes:
- Keep your work inside `/root/workspace/` and `/root/workspace/out/`.
- Do not modify files under `/root/workspace/spec/`.
- Do not modify tests, verifier files, task metadata, or environment files.
- Do not require browser wallets, private keys, external RPC endpoints, block explorers, or third-party accounts.
- Do not replace the Solidity protocol with an off-chain calculator, a static JSON file, or a mocked report.
- Do not hardcode final balances, rewards, votes, or report fields.
- You may add helper contracts and scripts inside `/root/workspace/`, but keep the entrypoint path and output path unchanged.
