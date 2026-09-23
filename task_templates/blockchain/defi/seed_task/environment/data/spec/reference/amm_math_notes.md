# AMM Notes

- A constant-product pool keeps two reserves and updates them after each liquidity or swap action.
- Initial LP shares typically start from the square root of the two seeded reserve amounts.
- Later LP share mints usually follow the smaller proportional contribution across the two reserve sides.
- Exact-input swaps apply the configured fee before computing output against the opposite reserve.
- When fee stays positive, the post-swap reserve product should not move below the pre-swap reserve product for a well-formed swap path.
