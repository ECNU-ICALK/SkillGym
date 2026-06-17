# Curation Brief

The editorial team is preparing a compact highlight feed for four audience lanes.

Publishing rules:
- A highlight can enter the public feed only when its source artwork is marked ready for highlight use.
- Ready for highlight use requires both public-domain clearance and a non-empty primary image URL from the provided source snapshot.
- Seeded lane assignments and sort orders come from `met_objects_seed.csv`.
- The public feed must stay ordered by lane key ascending and then `sortOrder` ascending within each lane.
- Every public feed item must carry the lane title, the editorial display title for that highlight slot, artist name, department, object date, image URL, source URL, and sort order.
- Editors may prepare draft highlight records, but only curators and admins may control publish state or feed ordering.
- Editors work from personal draft queues. A newly created editor draft should be attributed to that editor automatically, and editors should not be able to read or modify another editor's draft work queue.
- The generated summary file should report `publishedHighlights` as the number of highlights that currently qualify for the public feed after publish, readiness, and lane-scope rules are applied.
