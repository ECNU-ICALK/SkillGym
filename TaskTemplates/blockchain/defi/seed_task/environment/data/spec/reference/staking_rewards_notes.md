# Staking Reward Accounting Notes

- Reward accrual is time-based and should update from the prior checkpoint to the current timestamp.
- When no LP shares are staked, global reward-per-token should stay unchanged.
- User earnings depend on the delta between the current reward-per-token value and the user's paid checkpoint, scaled by staked balance.
- If a new reward funding event arrives before the active period ends, the remaining undistributed value must stay represented in the next reward rate.
- Claims should move accrued reward from internal accounting to token transfer without exceeding funded balances.
