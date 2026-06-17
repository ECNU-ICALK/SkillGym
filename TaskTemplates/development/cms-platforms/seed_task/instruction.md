You are taking over a Payload CMS workspace under `/app/workspace/` for a curatorial editing team. You need to turn the provided collection data into a manageable, publishable curated-content backend that can be consumed by the public-facing frontend.

Input data is under `/app/data/`:
- `met_objects_seed.csv`: seed collection objects plus mappings for highlight slots and editorial slots.
- `met_departments.json`: department list and department IDs.
- `met_object_details.ndjson`: snapshot of collection object details.
- `curation_brief.md`: curation publishing rules and business constraints.
- `audience_lanes.json`: frontend audience-lane configuration.
- `seed_users.json`: initial admin users and role data.

Your tasks
1. Complete the current CMS workspace so editors can manage collection items, creator/artist info, department affiliation, and highlight lanes, and so relationships between these entities remain usable.
2. Preserve the existing local startup and data rebuild entrypoints so `scripts/reseed.ts` can import or sync based on the task-provided data.
3. Ensure publishing behavior satisfies the business constraints in `curation_brief.md`; the public feed must return only content that meets the publishing conditions.
4. Ensure different user roles have the correct operational scope in the admin UI, including draft ownership and visibility boundaries; unauthorized actions must not take effect.
5. Provide a public JSON endpoint `/api/highlight-lanes/feed` that supports filtering by `department`, `audience`, and `limit`.

Output:
- Directly modify project files under `/app/workspace/` and any required supporting files.
- After `scripts/reseed.ts` completes, generate `/app/workspace/output/seed-summary.json`. This file must be valid UTF-8 JSON and must include at least the following fields:
  - `departments`
  - `artists`
  - `artworks`
  - `highlightLanes`
  - `publishedHighlights`
  - `publishedHighlights` is the number of highlights that currently satisfy the conditions to appear in the public feed.
- After the local app starts, `/api/highlight-lanes/feed` must be accessible.
- Each record returned by the endpoint must include at least the following fields:
  - `lane`
  - `title`
  - `slug`
  - `artistName`
  - `department`
  - `objectDate`
  - `primaryImage`
  - `objectURL`
  - `sortOrder`
  - `title` is the title shown for the current highlight slot in the public feed.

Notes:
- You may add necessary project files, scripts, and helper code, but keep the existing run entrypoints and the main directory structure.
- You may add a small number of publicly installable dependencies, but do not introduce components that require external accounts, extra manual logins, or remote database permissions.
- Do not modify input files under `/app/data/` to evade the task requirements.
- Do not hard-code feed contents, counts, or slugs in code or static files.
- Do not reduce scope by removing content relationships, publishing constraints, role boundaries, or the public endpoint.
- Do not move management logic to an extra container or external service.
