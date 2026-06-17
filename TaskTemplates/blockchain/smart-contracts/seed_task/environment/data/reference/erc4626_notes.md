# ERC4626 Integration Notes

- ERC-4626 vault math assumes a consistent relationship between assets, shares, and rounding direction.
- Non-18-decimal assets often need explicit normalization before share accounting.
- Preview and conversion helpers are expected to stay aligned with the underlying asset behavior and fee model.
