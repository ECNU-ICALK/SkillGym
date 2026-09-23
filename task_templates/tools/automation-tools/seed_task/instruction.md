You need to deliver the changelog files for a bundled CLI release. The local workspace already includes the current changelog pages, the release payload, formatting rules, and the formal generation entrypoint. Use those local inputs to complete the release-doc delivery.

Input data is available under `/environment/reference_bundle/`:

- `workspace/docs/changelogs/index.md`: release landing page
- `workspace/docs/changelogs/latest.md`: stable release page
- `workspace/docs/changelogs/preview.md`: preview release page
- `release_payload/version.txt`: target version
- `release_payload/released_at.txt`: release timestamp
- `release_payload/body.md`: release notes body
- `release_payload/release_page.html`: release page snapshot
- `reference/releases.md`: release process reference
- `contracts/changelog_contract.json`: delivery contract
- `contracts/formatting_rules.json`: formatting rules
- `workspace/scripts/render_changelog.py`: formal build entrypoint
- `workspace/package.json`: formatting command config

Your tasks
1. Complete the changelog update from the provided release material and local contract files.
2. Keep the delivery aligned with the current docs workspace structure and writing style.
3. Keep the formal generation entrypoint usable so the same workspace can produce the required outputs again from the current inputs.
4. Generate the required review artifacts under the output directory.

Output
- Create `/environment/output/latest.md`.
- Create `/environment/output/preview.md`.
- Create `/environment/output/index.md`.
- Create `/environment/output/release_manifest.json`.

`release_manifest.json` must be valid JSON and include:
- `version`
- `release_channel`
- `release_kind`
- `release_date_iso`
- `release_date_long`
- `updated_files`
- `announcement_prs`
- `highlight_titles`
- `full_changelog_url`

Notes
- Do not modify the bundled release material, contract files, tests, or task metadata.
- Do not replace the local generation flow with a one-off manual export or hardcoded final artifacts.
- Do not invent change summaries, PR links, author names, or URLs that are not supported by the bundled materials.
- If needed, you may add a small helper under `/environment/reference_bundle/workspace/`. Final evaluation will use the formal generation entrypoint and the files under `/environment/output/`.
