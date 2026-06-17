# WordPress WooCommerce Development

Use this skill when a task asks you to build or complete a WooCommerce workspace that depends on platform setup, catalog seeding, shipping configuration, payment restrictions, and custom storefront behavior.

## Recommended workflow

1. Read the task data files first and identify the delivery contract before editing code.
2. Verify the platform baseline in the container:
   - confirm WordPress and WooCommerce are installed and active;
   - inspect the current plugin workspace under `/app/workspace/plugin`;
   - inspect the current reseed entrypoint under `/app/workspace/scripts/reseed.php`.
3. Derive the catalog target from the task data:
   - join the merchandising seed rows with the object detail snapshot;
   - determine which products should exist, which ones should be published, and which variations should be purchasable;
   - preserve object IDs, collection keys, department slugs, prices, stock, and SKU suffix logic.
4. Implement the store configuration inside WooCommerce instead of bypassing it:
   - create or update product categories, attributes, and variable products through WordPress or WooCommerce APIs;
   - configure shipping classes, shipping zones, and rate settings from the task rules;
   - configure payment gateway availability through WooCommerce hooks or settings rather than static endpoint logic.
5. Implement the public feed as a WordPress REST route backed by WooCommerce product data.
6. Rerun the reseed flow after each substantial change and inspect the resulting store state before final submission.

## Common failure patterns

- Writing the feed directly from source files without building the WooCommerce catalog.
- Creating products but skipping variation-level SKU, stock, or attribute setup.
- Updating gateway options but not enforcing cart-dependent payment visibility.
- Creating shipping zones but leaving locations, class costs, or titles incomplete.
- Hardcoding counts or feed rows instead of deriving them from task data on each reseed.

## Helper scripts

- `scripts/probe_expected_catalog.py`: prints derived catalog and feed expectations from the task data.
- `scripts/probe_store_state.sh`: prints active plugins, products, shipping classes, zones, and enabled gateways.
- `scripts/probe_launch_feed.sh`: queries the public feed endpoint with representative filters.

The helper scripts are intended to reduce diagnosis time. You are still responsible for matching the task's exact output contract and checking the final store behavior.
