You need to prepare a candidate-title shortlist workbench for a content curation team. The container provides a public title snapshot, an initial shortlist seed, a small set of startup scripts, and an empty workspace directory. The team requires you to build a complete Next.js App Router project from scratch inside this empty directory, using TypeScript and organizing the project under a `src/` directory, so they can filter candidate titles, view title details, and maintain an internal shortlist.

Input data is under `/app/data/`:
- `title_basics_sample.tsv`: snapshot of basic title metadata, including title, type, year, runtime, and genres
- `title_ratings_sample.tsv`: snapshot of ratings and vote counts
- `shortlist_seed.json`: initial shortlist seed
- `scripts/`: startup and basic check scripts

Your tasks
1. Build the complete project structure from scratch in `/app/workspace` and deliver a runnable Next.js App Router candidate-title workbench. The project must keep TypeScript, `src/app` page routing, JSON API routes within the same project, and the default install/build/start chain. The curation team must be able to browse candidate titles by title, `titleType`, year range, `genre`, minimum rating, and minimum votes, and must have stable sorting and pagination. Results must be computed from the input snapshots; do not hard-code fixed results.
2. Provide title details pages that display at least `tconst`, title, original title, type, year, runtime, genres, rating, and votes, and allow users to navigate from the list into the details view.
3. Provide shortlist management. Users must be able to add a title to the shortlist, edit `priority`, `status`, and `note`, and remove entries. Each shortlist entry must include at least `tconst`, `priority`, `status`, and `note`; `priority` must be one of `P1`, `P2`, `P3`, and `status` must be one of `watch`, `review`, `approve`, `hold`. These changes must persist across app restarts.
4. Provide overview information for team review, covering at least total shortlist count, distribution by `status`, average shortlist rating, and the current highest-rated shortlist entry; these stats must update as the shortlist changes.
5. Preserve the task-provided data chain, local persistence method, and default startup method. After startup, the deliverable must continue to support both interactive page usage and programmatic data access through the same Next.js project, meeting the three use cases: candidate browsing, details viewing, and shortlist management.

Output:
- Create the complete project structure under `/app/workspace` and implement the deliverable code.
- The deliverable must be a single-project Next.js App Router TypeScript application. Page routes must live under `src/app/`, and JSON APIs must be served by the same project.
- Keep the existing startup entrypoints; validation will start the app using the repository's default method.
- After startup, the deliverable must continue to provide candidate browsing, details viewing, and shortlist management.
- The deliverable must provide at least the following page routes:
  - `/`: candidate title browsing and filtering page
  - `/titles/:tconst`: single-title details and shortlist edit page
  - `/shortlist`: shortlist overview and entry list page
- The deliverable must provide the following JSON endpoints:
  - `GET /api/health`
  - `GET /api/titles`
  - `GET /api/titles/:tconst`
  - `GET /api/shortlist`
  - `POST /api/shortlist`
  - `PATCH /api/shortlist/:tconst`
  - `DELETE /api/shortlist/:tconst`
- `GET /api/titles` must support the following query parameters: `query`, `titleType`, `genre`, `yearFrom`, `yearTo`, `minRating`, `minVotes`, `sort`, `page`, `pageSize`

Notes:
- You may add necessary project structure, dependencies, data loading, validation, persistence, styles, and test helper code, but do not change the task goal.
- You may add a small number of dependencies, but do not introduce components that require external private accounts, manual logins, extra cloud permissions, or online databases.
- Do not modify input files under `/app/data/` to evade constraints.
- Do not turn the deliverable into static pages, screenshot pages, offline report-generation scripts, or one-off export scripts.
- Do not split this into two projects, a second service, a separate Node API process, a reverse-proxy layer, or an extra container.
- Do not hard-code results so they only work for a few specific titles, a few specific filter values, or a single path.
- Do not modify tests, verifier, task metadata, environment files, or any `skills` directory contents.
- Do not make the app depend on external private accounts, manual logins, online databases, or extra cloud permissions.
