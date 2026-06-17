You are taking over a country energy comparison workbench used by the regional strategy team. After the most recent frontend refactor, this workbench is no longer suitable as a stable internal delivery page: when users switch between filtering, searching, sorting, and country comparison, different areas of the page often show inconsistent state; after refreshing, navigating back/forward, or sharing the current link with a colleague, the previously selected filters and comparison context are often lost, mismatched, or restored incorrectly; the first load of the home page has become noticeably slower, with unnecessary waiting before users even expand deeper content; and on narrow screens and when using keyboard-only operation, the filter panel, comparison flow, and details panel often cannot be completed reliably. You need to fix the existing frontend without changing the product scope so the workbench again meets day-to-day analysis and sharing requirements.

Inputs are located at:
- `/app`: existing React / Vite frontend code, including the country list, filter bar, comparison workspace, details drawer, chart modules, and routing entrypoints
- `/data/owid_energy_snapshot.csv`: snapshot of country-year energy metrics, including generation mix, low-carbon share, generation totals, per-capita metrics, and more
- `/data/owid_energy_codebook.csv`: metric names, units, descriptions, and display metadata
- `/data/world_bank_countries.json`: snapshot of countries, regions, income groups, and baseline metadata
- `/services/energy-api`: local API service startup code within the same container; at runtime, the service response is the source of truth for data. The list and details views may only call it; they must not modify it.
- `/scripts`: frontend startup and basic check scripts

Your tasks
1. Fix the existing frontend so that country filtering, search, sorting, comparison, summary cards, chart highlight sections, and the details drawer are consistent under a single page state, and remain reliable after refresh, back navigation, forward navigation, and re-entering the page via the current link.
2. Fix page-state restoration. When users refresh, go back/forward, or re-enter the current page context, the key filter conditions, comparison targets, and current viewing context must all be restored correctly; do not evade the existing problems by introducing a parallel page.
3. Fix the initial-load issues on first entry. Before the user enters deeper secondary analysis flows, the page should load normally and support the primary browsing flow; when users later expand additional capabilities, the page must continue to work correctly and must continue to be based on real data from the local API.
4. Fix major interaction failures on narrow screens and for keyboard-only usage, ensuring the primary interaction flows can be completed reliably across common desktop and mobile viewports; do not evade real DOM interaction by using screenshots, full-page images, or a full-page canvas.
5. Preserve the existing product boundary, routing entrypoints, and local data chain, and continue using the task-provided data files and local API as the sources of truth.

Output:
- Directly modify the existing frontend code under `/app`.

Notes:
- Keep the existing startup entrypoints; validation will start the frontend and the local API using the repository's default method.
- After startup, the frontend must continue to provide country browsing, filtering, comparison, and details viewing; do not rewrite the task into static page export, offline report generation, or pure data-processing scripts.
- You may add necessary state handling, data transformations, component refactors, resource-loading controls, styles, accessibility attributes, and test helper code, but do not change the product goal of the task.
- You may add a small number of dependencies, but do not introduce components that require external private accounts, manual logins, extra cloud permissions, or external online services to validate.
- Do not modify input data under `/data` to evade the issues.
- Do not modify the local API service under `/services/energy-api`, and do not replace the real data chain.
- Do not evade the issues by removing the comparison workspace, chart highlight sections, details drawer, filtering capabilities, route state, or keyboard interactions.
- Do not spin up a second frontend, a second service, a reverse-proxy layer, or a static mocked data flow to bypass the existing implementation.
- Do not hard-code results so they only work for a fixed country, fixed year, fixed metric, or a single path.
- Do not require internet access during solve; the final result must be fully based on code, local data, and same-container services.
