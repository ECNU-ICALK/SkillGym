---
name: ccxt-python
description: Normalize exchange market catalogs and public OHLCV data in Python, especially when native symbols, timestamp units, and exchange-specific schemas differ.
---

# CCXT Python

Use this skill when a task asks you to work with public exchange market data in Python and the inputs involve exchange-native market identifiers, OHLCV payloads, or multi-exchange normalization.

## Recommended workflow

1. Read the contract first and list the required canonical symbols, exchanges, output files, and aligned-window rules.
2. Load each exchange catalog before touching the candle files. Keep three separate identities straight for every market:
   - the exchange-native market id from the catalog;
   - the source symbol present in the market-data file;
   - the canonical symbol required by the contract.
3. Normalize the OHLCV payloads into one common bar schema:
   - parse timestamps into UTC datetimes;
   - sort them in ascending time order;
   - detect quote-volume columns by name instead of assuming a single layout;
   - keep numeric columns as numbers all the way through the calculations.
4. For cross-exchange comparisons, do not use an exchange-only trailing row. Build the latest common window required by the contract and calculate all market metrics from that aligned slice.
5. Derive returns from close prices, derive 24-hour quote volume from the requested trailing window, and derive realized volatility from the requested return series.
6. Build the alert rows from the contract thresholds after the metrics are complete. Keep the CSV sorted exactly as requested.
7. In the runbook, name the manifest collection step explicitly and mention `/api/manifest`.
8. Run the project entrypoint after implementation and confirm that the delivered artifacts can be reproduced through the workspace project, not only through ad hoc helper code.

## Task-specific pitfalls

- The older reference export does not define the authoritative market set for this task.
- The live catalog is paginated, so one page is not enough to discover all required markets.
- Kraken uses `XBT` while the contract expects `BTC`, and both identities must stay traceable.
- OHLCV payloads do not all use the same bar order or volume unit.

## Helper script

- `scripts/build_candidate_report.py`: reads the task inputs and emits candidate surveillance outputs using the full workflow above. It does not write into the workspace project for you. Use it to confirm the manifest lookup, catalog traversal, symbol mapping, and metric conventions before you wire the logic into `/app/workspace/marketwatch/`.
