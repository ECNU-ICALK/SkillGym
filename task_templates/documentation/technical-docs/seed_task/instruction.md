You need to deliver a completed API documentation page for `PQueue` in a local
docs workspace. The workspace already includes a bundled release snapshot,
implementation files, behavior tests, local reference pages, and a delivery
contract. The target page is currently missing and the docs team needs a
rebuildable deliverable from the local workspace.

Write the page as a single API reference article, not as a report or an essay.
The page must open with one concise sentence, then show the top usage example
immediately as a TS/JS `switcher` pair, and only then start `## Reference`.
Every code block in the page must use both `filename="..."` and
`highlight={n}`.

Input data is available under `/environment/reference_bundle/`:

- `upstream/package.json`: package metadata for the bundled release snapshot.
- `upstream/source/index.ts`: the main `PQueue` implementation.
- `upstream/source/options.ts`: option types and related behavior notes.
- `upstream/test/test.ts`: behavior tests for queue execution, rate limiting,
  timeout handling, cancellation, and lifecycle behavior.
- `upstream/readme.md`: public usage examples and API snippets from the same
  release line.
- `upstream/release_v8.1.1.html`: bundled release page for this release
  snapshot.
- `contracts/page_contract.json`: the delivery contract. It defines the output
  path, frontmatter keys, required sections, required tables, required examples,
  required API items, and cleanup rules.
- `contracts/reference_rules.json`: local writing and formatting rules for the
  docs site.
- `contracts/version_notes.json`: required version-note entries for the final
  page.
- `/environment/workspace/docs/01-app/03-api-reference/`: local reference pages that
  show the docs-site structure and formatting shape.
- `/environment/workspace/build_reference.py`: the formal local build entrypoint for
  this delivery. It must remain the formal generation entrypoint.

Your tasks
1. Create the final documentation page at `/environment/output/pqueue_api_reference.mdx`.
2. Follow `page_contract.json` and complete the full page for `PQueue` using
   the bundled source files, tests, version notes, release page, and local
   reference material as the source of truth.
3. Deliver every contract-required API item, section, table, example, and
   version-note entry for the bundled release snapshot.
4. Keep the output suitable for direct review in the local docs site. Remove
   placeholder content, unfinished notes, draft markers, and delivery residue.
5. Generate `/environment/output/reference_manifest.json` for later review. It must
   record which bundled upstream files were used, which documented API items
   were delivered, which contract-required examples were included, and which
   version-note entries were included.
6. Keep the local build entrypoint usable so the team can regenerate the same
   outputs from the current inputs. Do not turn the task into a one-off manual
   export. The docs review step reruns the formal build entrypoint from the
   current workspace, so changes must land in that entrypoint and not only in
   prebuilt output files. Review runs may use the same build entrypoint with a
   nearby bundle variant from the same release line, so derive version strings,
   example titles, and behavior wording from the current bundle inputs instead
   of assuming fixed literals.
7. Ground key behavior claims in the bundled implementation, tests, and release
   snapshot. Review notes in the page and manifest should make it possible to
   trace the delivered claims back to the current local inputs.

Output shape reminder:
- One opening sentence only.
- Top example first, as a `ts` / `js` pair.
- `## Reference` after the top example pair.
- `## Good to know`, `## Examples`, and `## Version History` must appear in
  that order after the reference section.

Output
- Update the formal delivery code and any necessary supporting configuration
  under `/environment/workspace/`.
- Create exactly these files under `/environment/output/`:
  - `pqueue_api_reference.mdx`
  - `reference_manifest.json`

`reference_manifest.json` must include:

```json
{
  "page_path": "pqueue_api_reference.mdx",
  "api_name": "PQueue",
  "package_name": "p-queue",
  "package_version": "8.1.1",
  "source_files": [
    "upstream/package.json",
    "upstream/source/index.ts",
    "upstream/source/options.ts",
    "upstream/test/test.ts",
    "upstream/readme.md",
    "upstream/release_v8.1.1.html"
  ],
  "documented_api_items": [
    {
      "name": "string",
      "kind": "constructor or option or method or property or event",
      "required_sections": ["string"]
    }
  ],
  "example_ids": ["string"],
  "version_notes": [
    {
      "version": "string",
      "summary": "string"
    }
  ],
  "notes": ["string"]
}
```

Notes
- Do not modify the bundled upstream files, contract files, or local reference
  pages under `/environment/reference_bundle/` and
  `/environment/workspace/docs/`.
- Do not change the required output paths or filenames.
- Do not modify the tests, validation logic, pinned dependencies, environment
  or configuration files.
- Do not split the work across multiple pages.
- Do not narrow the delivery to a summary, a README rewrite, or a raw symbol
  listing without page-level explanation.
- Do not invent unsupported API items, defaults, return behavior, examples,
  version notes, or links that are not grounded in the bundled inputs.
- Do not copy long passages from the bundled upstream material line for line.
- You may add a small local helper script if needed, but the final evaluation
  will be based on the formal outputs in `/environment/output/` and the formal
  generation entrypoint under `/environment/workspace/`.
