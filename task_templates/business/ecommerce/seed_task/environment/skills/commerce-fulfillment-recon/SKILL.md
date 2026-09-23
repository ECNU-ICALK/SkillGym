# Commerce Fulfillment Reconciliation

Use this skill when a task asks you to reconcile ecommerce orders, product variants, warehouse reservations, and carrier tracking state. It is especially useful for Shopify-like Admin GraphQL workflows where order exports may be stale and the live API must be paginated.

## Recommended workflow

1. Read the merchant manifest and treat the live service URLs as authoritative.
2. Probe the Admin GraphQL endpoint before writing analysis code:
   - fetch orders with cursor pagination until `hasNextPage` is false;
   - fetch active product variants by SKU;
   - preserve `variantId`, `inventoryItemId`, fulfillment service, and line item IDs.
3. Join order line items to the catalog export by SKU.
4. For each unique resolved `inventoryItemId`, query warehouse stock and open reservations. Available stock is `on_hand - sum(open reservation quantities)`.
5. For each tracking number on shipped or in-transit items, query the carrier endpoint and normalize the latest carrier status before comparing it with the admin fulfillment status.
6. Emit one exception row per line item issue. Do not collapse multiple issue codes into a single row.

## Issue-code heuristics

- `SKU_VARIANT_DRIFT`: the SKU has zero active variants, more than one active variant, or the single active variant ID differs from the line item's variant ID.
- `FULFILLMENT_SERVICE_MISMATCH`: the active variant's fulfillment service differs from the catalog expectation.
- `INSUFFICIENT_AVAILABLE_STOCK`: the line item still needs units and available stock is below that unfulfilled quantity.
- `STALE_OR_CONFLICTING_TRACKING`: carrier latest status is `delivered`, `cancelled`, or `exception`, while the admin service still shows an in-progress state such as pending, unfulfilled, partial, or in transit.
- `MISSING_TRACKING_FOR_SHIPPED_ITEM`: the admin service says a physical item is shipped or fulfilled, but the carrier lookup has no valid record.

## Helper scripts

- `scripts/probe_admin_graphql.py`: paginated GraphQL probes for orders and active variants.
- `scripts/probe_downstream.py`: warehouse and carrier probes.
- `scripts/reconcile_candidates.py`: produces a generic JSON candidate set from a manifest and catalog. It does not contain task data or hard-coded answers; it derives rows from the live services.

The probe scripts are intended to reduce diagnosis time. You are still responsible for matching the task's exact output schema and checking the final files before submission.
