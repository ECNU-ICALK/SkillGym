# Integration Checklist

Use this checklist to translate token behavior into onboarding outcomes.

1. Start with the staged collateral path, not the token in isolation. The same token can be acceptable in one protocol shape and unsuitable in another.
2. Decide which protocol-side measure each behavior needs:
   - missing return values -> transfer wrapper
   - fee-on-transfer -> balance delta accounting
   - rebasing or balance drift -> external-balance resynchronization before share math
   - pause or blocklist controls -> explicit operational response path
   - upgradeability -> implementation-change monitoring
   - non-18 decimals -> normalization
   - approval quirks -> reset-and-approve handling
   - callbacks or hooks -> reentrancy protection
3. Inspect the staged contracts and mark each required measure as supported, partial, or missing.
4. Use the resulting gap profile to pick a decision:
   - baseline collateral with no extra triggered behaviors can remain in the low-friction path
   - supported transfer or precision accommodations can still require conditions
   - missing or partial operator-control coverage should move the token into review
   - unsupported accounting-critical or callback-critical gaps should block onboarding
