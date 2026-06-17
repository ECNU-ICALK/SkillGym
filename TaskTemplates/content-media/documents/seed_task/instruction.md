You need to deliver a North America energy briefing packet as a Word document. The workspace already includes a draft packet, public data snapshots, brand assets, and a delivery contract. The current packet is not ready for review. Complete the delivery while keeping the existing document shell, output paths, and data boundaries.

Input data is available under `/app/briefing/`:
- `drafts/briefing_draft.docx`: the current briefing draft. It already includes the cover, header, footer, section skeleton, contents location, chart slots, review residue, and appendix entry point.
- `contracts/briefing_contract.json`: the delivery contract. It defines section order, required tables, chart requirements, metric rules, naming rules, and cleanup requirements.
- `data/country_profile.json`: country profile data and document labels.
- `data/world_bank_population.json`: population snapshot.
- `data/world_bank_gdp.json`: GDP snapshot.
- `data/annual_co2_emissions.csv`: annual CO2 emissions snapshot.
- `data/electricity_prod_source.csv`: electricity generation by source snapshot.
- `notes/source_notes.md`: source notes, terminology notes, and delivery reminders.
- `/app/workspace/build_packet.py`: the current local build entrypoint. It must remain the formal generation entrypoint for this delivery.

Your tasks
1. Complete the final Word briefing packet and write it to `/app/output/north_america_energy_briefing.docx`.
2. Follow `briefing_contract.json` to complete the full packet. At minimum, the delivery must cover the executive summary, country comparison, electricity mix, emissions trend, source notes, and appendix. Use the local data files and the contract as the source of truth for metrics, country order, section order, and chart captions.
3. Replace the draft placeholders for tables, charts, and section content with final delivery content. Every chart and table required by the contract must appear in the final document.
4. Do not stop at raw tables and chart captions. The `Country Snapshot`, `Electricity Mix`, and `CO2 Trend` sections each need a short explanatory paragraph that interprets the data shown in that section.
5. Place those explanatory paragraphs inside the section where they belong. In particular, `Country Snapshot` needs an explanatory paragraph in that section after the comparison table, and the chart sections need explanatory prose in their own sections rather than pushing all interpretation into the executive summary.
6. In `Source Notes`, include the bundled source references together with the applicable metric-year and formatting rules, but rewrite the reminder language into packet-ready prose instead of copying reminder bullets or reminder sentences line for line.
7. Keep the local build entrypoint usable so the team can regenerate the same delivery from the current inputs. Do not turn the task into a one-off manual edit.
8. Keep the existing cover, headers, footers, page numbering, section order, contents location, appendix entry point, and document styling from the draft. Do not replace the task with a separate document shell that avoids those requirements.
9. Clean the document so it is ready to send to reviewers. Do not leave placeholder text, example paragraphs, empty tables, empty chart areas, review residue, temporary notes, `TODO`, `TBD`, or demo text in the final document.
10. Generate `/app/output/briefing_manifest.json` to record the input files used for the delivery, the final section order, table identifiers, chart identifiers, and the key metric years for later review.

Output
- Update the formal delivery code and any necessary supporting configuration under `/app/workspace/`.
- Create exactly these files under `/app/output/`:
  - `north_america_energy_briefing.docx`
  - `briefing_manifest.json`

`briefing_manifest.json` must include:

```json
{
  "document_path": "north_america_energy_briefing.docx",
  "countries": ["Canada", "Mexico", "United States"],
  "source_files": [
    "data/country_profile.json",
    "data/world_bank_population.json",
    "data/world_bank_gdp.json",
    "data/annual_co2_emissions.csv",
    "data/electricity_prod_source.csv"
  ],
  "sections": [
    {
      "title": "string",
      "table_ids": ["string"],
      "chart_ids": ["string"]
    }
  ],
  "key_metrics": {
    "population_year": 0,
    "gdp_year": 0,
    "co2_year": 0,
    "electricity_year": 0
  },
  "notes": ["string"]
}
```

Notes
- Do not modify the input data, contract files, or source notes under `/app/briefing/`.
- Do not change the required output paths or filenames.
- Do not modify the tests, validation logic, pinned dependencies, environment configuration, or skill files.
- Do not narrow the delivery to only a summary, only a small subset of the tables, or only plain exported text.
- Do not rely on hardcoded single-year logic, single-country logic, fixed paragraphs, fixed chart captions, or special cases that only work for one visible snapshot.
- Do not change the main delivery into a PDF, HTML, Markdown file, plain text file, image bundle, or external online document.
- You may add a small local helper script if needed, but the final evaluation will be based on the formal outputs in `/app/output/` and the formal generation entrypoint under `/app/workspace/`.
