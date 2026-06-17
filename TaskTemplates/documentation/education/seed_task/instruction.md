You are preparing a rerunnable teaching notebook for an education policy and data literacy workshop. The course team has already placed this round's data extracts, metric notes, teaching goals, and chart requirements in the workspace. They expect a teaching assistant to be able to run the notebook from top to bottom and use it to guide learners through one complete workflow: reading the raw tables, cleaning fields, aligning years, comparing indicators, and closing with evidence-based takeaways.

Input data is available in `/root/workspace/source_bundle/`:

- `lesson_brief.md`: workshop audience, teaching goals, comparison scope, and conclusion boundaries
- `years_of_schooling.csv`: years-of-schooling indicator extract
- `school_enrolment.csv`: enrolment indicator extract
- `education_spending.csv`: education spending indicator extract
- `metric_notes.md`: metric definitions, units, and year-coverage notes
- `country_cohort.csv`: allowed entities and cohort grouping metadata
- `chart_requirements.json`: required chart topics and minimum chart expectations
- `analysis_rules.md`: required rules for cleaning, year selection, aggregation, and claim boundaries

Your task

1. Build one teaching notebook for workshop learners from the provided data and written guidance.
2. Show the full workflow in the notebook, from loading raw inputs through harmonization, year alignment, comparison, and charting, while covering the chart topics required by `chart_requirements.json`.
3. Make the notebook usable as a complete classroom handoff for a teaching assistant working from the provided lesson packet.
4. Export one machine-readable indicator table and one short lesson summary so the course team can review the notebook outputs.

Output

If `/root/output/` does not exist, create it first. Write all deliverables to `/root/output/`, and only create these files:

- `global_education_tutorial.ipynb`
- `cohort_indicator_table.csv`
- `lesson_summary.json`

`global_education_tutorial.ipynb` requirements:

- It must be a runnable Jupyter notebook.
- The first cell must be Markdown and explain the notebook topic and how to use it.
- Near the start, identify the intended audience and the learning goals for the handoff.
- It must contain at least 3 topic sections.
- Include one short learner practice activity with a starter code cell.
- Include one note about an interpretation risk or limitation and one optional next step for classroom follow-up.
- Its code cells must run from top to bottom and produce the results shown in the notebook.
- If a teaching assistant reruns the notebook after removing old exports from `/root/output/`, the notebook must recreate the required CSV and JSON deliverables in the same location.

`cohort_indicator_table.csv` requirements:

- It must include a header row.
- Columns must appear in this exact order: `entity,entity_type,indicator,year,value,unit`.
- Keep only the entities allowed by `country_cohort.csv`.
- Cover the indicators and years that must be retained under `analysis_rules.md`.
- Sort rows by `entity`, `indicator`, and `year` in ascending order.

`lesson_summary.json` must match this structure:

```json
{
  "lesson_topic": "string",
  "target_audience": "string",
  "latest_common_year": 0,
  "entities_covered": ["string"],
  "takeaways": [
    {
      "rank": 1,
      "title": "string",
      "detail": "string",
      "evidence": [
        {
          "entity": "string",
          "indicator": "string",
          "year": 0,
          "value": 0.0
        }
      ]
    }
  ],
  "caveats": ["string"]
}
```

Requirements:

- `entities_covered` must match the final entity set in the exported cohort table.
- Provide at least 3 takeaways, ordered by increasing `rank`.
- Each takeaway must include at least 2 evidence rows.
- The takeaways must cover all 3 comparison dimensions in this lesson: `mean_years_schooling`, `gross_upper_secondary_enrolment_pct`, and `education_spending_pct_gdp`.
- At least 2 takeaways must use same-year evidence drawn from `latest_common_year`. If you include a trend takeaway, only cite values from the `2018-2022` window that also appear in the exported cohort table.
- `latest_common_year` must be the shared year you actually use for horizontal comparison.
- Include at least one caveat that explains the aligned-year boundary for the same-year comparisons.

Notes

- Use only files from `/root/workspace/source_bundle/` for analysis, writing, and numeric values.
- Do not add country groupings, years, values, conclusions, or policy advice that are not provided by or derivable from the input materials.
- Do not skip the cleaning and alignment steps. The notebook must make intermediate work visible to a teaching assistant.
- Do not modify the input directory, tests, or environment files.
- You may create helper scripts or temporary working files while solving the task. The final deliverables must remain only the 3 required files under `/root/output/`.
