You need to complete an engineering release watch workspace for a terminal-based update digest. The workspace already includes a digest shell, a tracked-source registry, bundled public source mirrors, a local watch database with prior history, and a delivery contract. Keep the existing build entrypoint, output paths, watch database path, and repeat-run workflow intact.

Input data is in `/app/release-watch/`:
- `drafts/engineering_release_digest.md`: the current digest shell with the required title, section order, and source-coverage shell.
- `contracts/digest_contract.json`: the delivery contract for output files, workspace state files, ranking rules, audit logging, and repeat-run behavior.
- `data/watch_targets.csv`: the tracked-source registry with source ids, labels, priority tiers, public source URLs, mirror snapshot paths, and optional feed override fields.
- `data/review_reopen_targets.csv`: the one-time review reopen list for this delivery.
- `data/mirror/`: bundled HTML pages and RSS/Atom snapshots for this task.
- `seed/initial_watch_state.json`: the seeded watch-state reference used when the local watch database must be restored.
- `notes/editor_notes.md`: delivery reminders and copy constraints.
- `/app/workspace/build_digest.py`: the formal local build entrypoint for this delivery.

Your tasks
1. Complete the local release-watch workflow and generate `/app/output/engineering_release_digest.md`.
2. Use the delivery contract, the tracked-source registry, the review reopen list, the bundled mirrors, the seeded watch-state reference, and the existing local watch database as the source-of-truth inputs for this run.
3. Keep the local tracker aligned to the tracked-source registry, remove any legacy blogs that remain only in the seeded local tracker but are no longer present in the tracked-source registry, preserve prior read history that already exists in the watch database, and keep unchanged reruns working from the same persisted workspace state.
4. Before selecting the delivery set for this run, consume the one-time review reopen list through the local watch workflow, persist repeat-run reopen tracking in the contract-defined workspace state file, and do not consume the same review targets again on unchanged later reruns after they have already been applied once.
5. Deliver only the contract-allowed unread backlog for this run, then persist the resulting watch state so unchanged reruns continue the remaining backlog instead of re-delivering it or collapsing it early.
6. Maintain the contract-defined audit log during each build run. Record registry add/remove actions, the main scan action, per-article review reopen actions, and per-article delivered-item read actions as separate `build`-stage CLI audit events, with each `args` list matching the invoked CLI tokens after the binary.
7. Keep bundle-relative mirror references bundle-relative in the inventory and manifest, and clean the final deliverables for review.

Output
- Update the formal delivery code under `/app/workspace/` and add only a very small helper there if it is strictly necessary for the build entrypoint.
- Create only these files under `/app/output/`:
  - `engineering_release_digest.md`
  - `feed_inventory.json`
  - `delivery_manifest.json`

`engineering_release_digest.md` must:
- include the title `# Engineering Release Watch`
- include the sections `## High Priority` and `## Standard Priority` in that order
- list delivered items as Markdown bullets under the applicable section
- include the source label, article title, published date, and article URL in each delivery bullet
- write `No new items.` under a required section when that section has no delivered items
- keep `## Source Coverage` in the digest
- if any legacy blogs were removed during this run, add the exact lead-in line `Removed legacy blogs for this run:` there and then list each removed blog name once as a Markdown bullet

`feed_inventory.json` must include:

```json
{
  "tracked_sources": [
    {
      "source_id": "string",
      "label": "string",
      "priority_tier": "string",
      "homepage_url": "string",
      "resolved_feed_reference": "bundle-relative data/... path string",
      "content_format": "rss|atom",
      "article_count": 0,
      "unread_count": 0,
      "latest_published_at": "ISO-8601 string"
    }
  ],
  "removed_blog_names": ["string"],
  "notes": ["string"]
}
```

`feed_inventory.json` should report each `unread_count` from the watch database state before this run marks its delivered items as read.

`delivery_manifest.json` must include:

```json
{
  "digest_path": "engineering_release_digest.md",
  "delivered_article_urls": ["string"],
  "read_marked_article_urls": ["string"],
  "reopened_article_urls": ["string"],
  "tracked_source_ids": ["string"],
  "removed_blog_names": ["string"],
  "source_files": ["bundle-relative source-of-truth path string"],
  "state_db_path": "string",
  "reopen_state_file": "string",
  "notes": ["string"]
}
```

Notes
- Do not modify the bundled inputs under `/app/release-watch/`.
- Keep the contract-defined watch database file in the workspace. It is part of the required workflow even though it is not an `/app/output/` deliverable.
- Keep the contract-defined audit log file in the workspace. It is part of the required workflow even though it is not an `/app/output/` deliverable.
- Keep the contract-defined reopen state file in the workspace. It is part of the required workflow even though it is not an `/app/output/` deliverable.
- The contract-defined reopen state file is a workspace JSON file for repeat-run tracking. It must keep an `applied_urls` array containing the review-target article URLs already consumed by the one-time reopen workflow on prior unchanged runs.
- Use the local watch workflow for review reopen transitions and delivered-item read transitions. Do not update article read state by writing directly to the article rows.
- Do not bulk-complete unread backlog that has not yet been delivered.
- In both `feed_inventory.json` and `delivery_manifest.json`, `removed_blog_names` must report the legacy blogs removed while reconciling this run.
- If the seeded local tracker still contains a legacy blog that is absent from the tracked-source registry, remove it during this run and report it through the required `removed_blog_names` fields and the Source Coverage section.
- In `delivery_manifest.json`, write the contract-defined watch database file string in `state_db_path`. Do not expand it to an absolute path.
- In `delivery_manifest.json`, write the contract-defined reopen state file string in `reopen_state_file`.
- `resolved_feed_reference` values and bundled mirror entries in `source_files` should stay bundle-relative and keep their `data/` prefix.
- `source_files` is an audit list of the source-of-truth files used for watch-state restoration, one-time review reopen processing, and feed resolution in this run. It must include `contracts/digest_contract.json`, `data/watch_targets.csv`, the bundle-relative reopen target file, the bundle-relative seeded watch-state file `seed/initial_watch_state.json`, and the bundled mirror files actually used to resolve each tracked feed. Do not add bundled implementation-side database snapshots or other derived runtime helper files there. Sort `source_files` lexicographically before writing `delivery_manifest.json`.
- If a source uses its homepage mirror to discover a feed, include both the homepage snapshot path and the resolved feed snapshot path in `source_files`. If a source uses a feed override, include that feed snapshot path.
- The output directory is a delivery directory. When the task ends, it must contain only the required deliverables.
