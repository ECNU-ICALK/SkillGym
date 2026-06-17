You are taking over a WooCommerce workspace under `/app/workspace/` for a museum shop launch week. You need to turn the provided collection assets into a sellable, manageable art print shop that can be consumed by the public-facing frontend.

Input data is under `/app/data/`:
- `met_print_seed.csv`
- `met_object_details.ndjson`
- `met_departments.json`
- `collection_plan.json`
- `shipping_rules.json`
- `checkout_policy.md`
- `seed_users.json`

Your tasks
1. Complete the current WooCommerce workspace so the operations team can import or sync products from the input data, while preserving the business relationships between artworks, creators/artists, departments, and thematic collections/series.
2. Preserve the existing local startup and data rebuild entrypoints so that after `scripts/reseed.php` runs, the data import, store configuration, and public content preparation are completed.
3. Ensure the store satisfies the business constraints in `collection_plan.json`, `shipping_rules.json`, and `checkout_policy.md`, and ensure those constraints are enforced both in the admin and in the storefront behavior.
4. Provide a public JSON endpoint `/wp-json/harbor-printshop/v1/launch-feed` that returns publishable products per the task requirements.
5. After the data rebuild completes, generate `/app/workspace/output/seed-summary.json`.

Output:
- Directly modify project files under `/app/workspace/` and any required supporting files.
- After `scripts/reseed.php` completes, generate `/app/workspace/output/seed-summary.json`. This file must be valid UTF-8 JSON and must include at least the following fields:
  - `products`
  - `variableProducts`
  - `variations`
  - `departments`
  - `collections`
  - `shippingZones`
  - `paymentGateways`
  - `launchFeedCount`
- The counts in `seed-summary.json` must reflect the current results after a complete data rebuild: `products`, `variableProducts`, and `variations` correspond to the WooCommerce catalog; `departments` and `collections` correspond to the de-duplicated departments and thematic collections/series associated with the imported products; `shippingZones` corresponds to the configured shipping zones; `paymentGateways` corresponds to enabled payment methods; `launchFeedCount` corresponds to the number of launch-feed entries under default conditions.
- After the local app starts, `/wp-json/harbor-printshop/v1/launch-feed` must be accessible.
- The payment rules in `checkout_policy.md` must not remain only as settings; the relevant payment methods must change at runtime based on cart conditions.
- Each record returned by the endpoint must include at least the following fields:
  - `productId`
  - `title`
  - `slug`
  - `artistName`
  - `department`
  - `collection`
  - `sku`
  - `price`
  - `image`
  - `availability`

Notes:
- You may add necessary themes, plugins, scripts, and helper code, but keep the existing run entrypoints and the main directory structure.
- You may add a small number of publicly installable dependencies, but do not introduce components that require external accounts, extra manual logins, or remote database permissions.
- Do not modify input files under `/app/data/` to evade task requirements.
- Do not hard-code feed contents, counts, SKUs, or product slugs in code or static files.
- Do not reduce scope by removing business relationships, store constraints, or the public endpoint.
- Do not move store logic to an extra container or external service.
