You need to deliver a browser-run briefing deck for a North America power mix review. The workspace already includes a delivery contract, page outlines, wireframes, public data snapshots, brand tokens, and a local build entrypoint. Complete the delivery while keeping the required output paths, data boundaries, and build flow.

Input data is available under `/app/power_brief/`:

- `contracts/layout_contract.json`: the delivery contract. It defines the required page ids, page order, required modules per page, chart requirements, metric rules, navigation requirements, and cleanup requirements.
- `outlines/slide_outline.json`: the page titles, key points, and note summaries for the briefing flow.
- `notes/editorial_notes.md`: editorial direction, tone constraints, and page-level reminders.
- `wireframes/`: low-fidelity page mockups for the required page sequence.
- `data/country_profile.json`: country labels and profile data used by the briefing deck.
- `data/world_bank_population.json`: population snapshot.
- `data/world_bank_gdp.json`: GDP snapshot.
- `data/annual_co2_emissions.csv`: annual CO2 emissions snapshot.
- `data/electricity_prod_source.csv`: electricity generation by source snapshot.
- `assets/brand_mark.svg`: the brand mark used in the site chrome.
- `assets/brand_tokens.json`: approved color, type, and spacing tokens for the delivery.
- `/app/workspace/build_site.py`: the current local build entrypoint. It must remain the formal generation entrypoint for this delivery.

Your tasks

1. Complete the final briefing deck and write it to `/app/output/north_america_power_mix_brief.html`.
2. Follow `layout_contract.json` to complete the full deck. At minimum, the delivery must cover the cover page, agenda, country snapshot, power mix comparison, emissions trend, implications, and appendix. Use the contract and the local data files as the source of truth for page order, required modules, chart captions, metric years, and copy limits.
3. Use `slide_outline.json`, `editorial_notes.md`, and `wireframes/` to complete the required page content and page structure. Every module required by the contract must appear in the final delivery, including three evidence-led implication cards that cover GDP scale, the lowest latest annual CO2 total, and the latest clean-generation lead.
4. Every required chart and table must appear together with its related explanatory text in the same page section.
5. The final delivery must be a single HTML file that can run directly in a browser from a local file path.
6. Every page must fit within one viewport with no internal scrolling while remaining readable at the required screen sizes.
7. Keep the local build entrypoint usable so the team can regenerate the same delivery from the current inputs.
8. Clean the site so it is ready for review. Do not leave placeholder text, sample copy, empty modules, review residue, `TODO`, `TBD`, or demo text in the final delivery.
9. Generate `/app/output/site_manifest.json` to record the input files used for the delivery, the final page order, chart identifiers, embedded assets, and the key metric years used in the site.

Output

- Update the formal delivery code and any necessary supporting configuration under `/app/workspace/`.
- Create exactly these files under `/app/output/`:
  - `north_america_power_mix_brief.html`
  - `site_manifest.json`

`site_manifest.json` must include:

```json
{
  "site_path": "north_america_power_mix_brief.html",
  "pages": [
    {
      "page_id": "string",
      "title": "string",
      "source_outline_index": 0,
      "chart_ids": ["string"],
      "module_ids": ["string"],
      "key_data_files": ["string"]
    }
  ],
  "source_files": [
    "data/country_profile.json",
    "data/world_bank_population.json",
    "data/world_bank_gdp.json",
    "data/annual_co2_emissions.csv",
    "data/electricity_prod_source.csv"
  ],
  "key_metrics": {
    "population_year": 0,
    "gdp_year": 0,
    "co2_year": 0,
    "electricity_year": 0
  },
  "embedded_assets": ["string"],
  "notes": ["string"]
}
```

Notes

- Do not modify the input data, contract files, notes, wireframes, or assets under `/app/power_brief/`.
- Before implementation, check whether a relevant local skill is available under `/root/.codex/skills/` and use it only as read-only workflow guidance when present.
- In `site_manifest.json`, list only the data files directly used by each page. Do not pad a page with unrelated data files just because they exist elsewhere in the deck.
- Keep manifest notes about the delivery and the bundled data. Do not include runtime checks, environment paths, or process commentary in the final outputs.
- Do not change the required output paths or filenames.
- Do not modify the tests, validation logic, pinned dependencies, environment configuration, or skill files.
- Do not turn the delivery into a PDF, a slide export, a Markdown report, an image bundle, or a multi-page website.
- Do not turn the delivery into a continuous scrolling webpage. Keep it as a page-based local-file briefing deck with working navigation.
- Do not narrow the task to only a summary, only a subset of the required pages, or only static screenshots.
- Do not rely on hardcoded single-year logic, single-country logic, fixed page count logic, or placeholder replacement that only works for one visible fixture.
- You may add a small local helper script if needed, but the final evaluation will be based on the formal outputs in `/app/output/` and the formal generation entrypoint under `/app/workspace/`.
