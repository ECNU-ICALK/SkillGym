# ERC20Votes Notes

- Voting power follows delegated checkpoints instead of raw token balances.
- A holder must delegate before their balance contributes active voting weight.
- Snapshot lookups depend on prior blocks, so proposal threshold and voting checks should use historical vote state.
- Transfers after delegation should update the relevant checkpoints for sender and receiver delegates.
- Queue and execute flows should only proceed after the vote window and configured delay constraints are satisfied.
