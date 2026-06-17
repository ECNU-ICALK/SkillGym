# Weird Token Patterns

Use this note together with the staged token profiles when deciding which protocol-side measures a candidate token needs.

- Missing return values still appear in production tokens. Integrations should use wrapper logic that treats non-reverting no-return calls safely.
- Fee-on-transfer tokens require received-amount accounting. Requested transfer amounts are not enough.
- Rebasing or balance-drift tokens should not be onboarded into share-based vault math unless the vault can resynchronize external balances before pricing shares.
- Pause or blocklist controls create an operations dependency. If the protocol has no clear response path, the token should not move straight to routine approval.
- Upgradeable tokens need implementation-change monitoring. Observation-only hooks are weaker than enforced change checks.
- Non-18-decimal tokens need normalization before share math and reporting.
- Legacy approval quirks require reset-and-approve handling.
- Hook or callback behavior requires explicit reentrancy protection around collateral movement.
