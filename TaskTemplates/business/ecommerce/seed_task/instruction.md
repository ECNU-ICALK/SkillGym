You are helping a merchant operations team decide which recent orders should be held before the morning shipping cutoff.

Input data is available in `/root/data/`:

- `merchant_manifest.json`: merchant context, reconciliation window, and service base URLs.
- `catalog_export.csv`: exported catalog and expected fulfillment routing data.
- `order_snapshot.ndjson`: an older platform export that may be incomplete or stale.
- `carrier_status_codes.csv`: carrier status reference data.

Your task

1. Review the orders that fall inside the reconciliation window and determine which paid, shippable line items require manual attention before release.
2. Cross-check the current commerce, catalog, warehouse, and shipment state, then classify every exception row with one of the allowed issue codes below.
3. Produce an operations-ready line-item report plus a short summary for the shipping manager.

Write your outputs to `/root/output/`. Create the directory if it does not exist.

Output

1. `/root/output/fulfillment_exceptions.csv`

The CSV must include these columns:

- `order_id`
- `order_name`
- `line_item_id`
- `sku`
- `variant_id`
- `issue_code`
- `severity`
- `expected_action`
- `evidence`

Use one row per line-item exception. If multiple issues apply to the same line item, output multiple rows.

Allowed `issue_code` values:

- `SKU_VARIANT_DRIFT`: the ordered item no longer cleanly matches the current active catalog variant.
- `FULFILLMENT_SERVICE_MISMATCH`: the current catalog routing does not match the expected fulfillment path for that SKU.
- `INSUFFICIENT_AVAILABLE_STOCK`: the current available inventory cannot cover the remaining unfulfilled quantity.
- `STALE_OR_CONFLICTING_TRACKING`: the latest shipment state materially conflicts with the commerce admin fulfillment state.
- `MISSING_TRACKING_FOR_SHIPPED_ITEM`: the item is marked shipped or fulfilled but no valid tracking record is available.

Allowed `severity` values:

- `critical`
- `high`
- `medium`

`expected_action` must be a short operational action.

`evidence` must be valid JSON stored in a single CSV field. It should contain enough source identifiers and checked systems for an operations reviewer to audit the row.

2. `/root/output/order_reconciliation_summary.json`

The JSON file must include:

- `window`
- `totals`
- `issue_counts`
- `source_checks`
- `notes`

`totals.exception_rows` must match the number of CSV rows. Include every allowed issue code in `issue_counts`, even when the count is `0`.

Notes:

- The current in-container services are the source of truth for order, catalog, stock-reservation, and shipment state.
- `order_snapshot.ndjson` is only a reference export. Do not treat it as the final source of truth.
- Do not modify files under `/root/data/`, the running services, or the verifier files.
- Do not replace the live service chain with mocks, cached answers, or alternative shortcuts.
- Do not delete functionality, stop background services, or change service responses to make the task easier.
- You may write helper scripts in the working directory, but the only required deliverables are the two files under `/root/output/`.

