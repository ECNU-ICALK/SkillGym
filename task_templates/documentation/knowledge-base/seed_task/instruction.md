You need to refresh the resource shelf for a JavaScript concept page about Promises and async/await. The workspace already includes the current page draft, a bundled candidate pool, a link-audit snapshot, and a delivery contract. Keep the existing page shell, output paths, and input boundaries intact.

Input data is in `/app/knowledge-base/`:
- `docs/promises-and-async-await.mdx`: the current concept page draft. It already includes frontmatter, concept copy, anchors, the current resource blocks, and editorial residue.
- `contracts/resource_contract.json`: the delivery contract. It defines the required structure, section counts, selection rules, cleanup rules, and output constraints.
- `data/candidate_resources.json`: the bundled candidate resource inventory.
- `data/link_audit_snapshot.json`: the bundled URL status and canonical-link snapshot for draft and candidate resources.
- `data/source_excerpts/`: bundled short descriptions for candidate resources.
- `notes/editor_notes.md`: editorial constraints and release reminders.
- `/app/workspace/curate_resources.py`: the formal local build entrypoint for this delivery. Keep it usable so the page can be regenerated from the current inputs.

Your tasks
1. Complete the final concept resource page and write it to `/app/output/promises-and-async-await.mdx`.
2. Use `resource_contract.json` and the bundled data files as the source of truth for page structure, section coverage, resource selection, cleanup, and output content.
3. Update the resource sections so the final page uses a publishable resource set while preserving the existing frontmatter, concept copy, anchors, and surrounding page shell.
4. Write `/app/output/resource_audit_report.md` to record the resource changes for this delivery.
5. Generate `/app/output/resource_manifest.json` with the final selected resources and the metadata required by the contract.
6. Clean the final deliverables for review. Do not leave placeholder cards, reviewer notes, `TODO` text, demo links, or empty required sections.

Output
- Update the formal delivery code under `/app/workspace/` and only add a very small helper there if it is strictly necessary for the build entrypoint.
- Create only these files under `/app/output/`:
  - `promises-and-async-await.mdx`
  - `resource_audit_report.md`
  - `resource_manifest.json`

`resource_manifest.json` must include:

```json
{
  "page_path": "promises-and-async-await.mdx",
  "concept_slug": "promises-and-async-await",
  "selected_resources": [
    {
      "id": "string",
      "title": "string",
      "section": "string",
      "resource_type": "string",
      "url": "string",
      "canonical_url": "string",
      "publication_year": 0,
      "status_code": 0,
      "reason_tags": ["string"]
    }
  ],
  "section_counts": {
    "reference": 0,
    "articles": 0,
    "videos": 0,
    "books": 0
  },
  "notes": ["string"]
}
```

Notes
- Do not modify the bundled input data, contract files, or notes under `/app/knowledge-base/`.
- Do not change the required output paths or filenames.
- Do not modify the tests, validation logic, pinned dependencies, or environment configuration.
- Do not narrow the delivery to only a report, only a link list, or only part of the required resource sections.
- Do not rely on hardcoded visible titles, hand-written final output that only works for the current bundle, or one-off cases tied to a single candidate resource.
- `resource_audit_report.md` must include these headings:
  - `## Removed or Replaced`
  - `## Redirect Updates`
  - `## Added Resources`
  - `## Coverage Check`
