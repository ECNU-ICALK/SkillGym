You are preparing a 2026 observance schedule pack for a small folk-culture studio. The candidate observances and operating constraints are already in the workspace. Your job is to resolve the calendar dates, choose the final program slate, and prepare the delivery files.

Input data is in:

- `/root/environment/data/brief/`: project request, delivery contract, and studio context
- `/root/environment/data/catalog/`: candidate observances, audience tags, and program notes
- `/root/environment/data/ops/`: blackout dates, staffing rules, weekday limits, and spacing rules
- `/root/environment/data/policy/`: final selection rules and output requirements
- `/root/environment/data/reference/`: supporting calendar reference material for cross-checks
- the environment also contains a provisioned 2026 calendar dataset for primary date resolution

Your tasks

1. Resolve the 2026 Gregorian date for every candidate observance in the catalog from the provisioned calendar dataset, and keep supporting evidence for each selected date.
2. Select exactly 4 observances that satisfy the scheduling and program constraints.
3. Prepare the final delivery pack with the selected schedule, the full date-resolution record, the supporting evidence bundle, and a short handoff note. Use the public reference files only as cross-check material.

Output:

If `/root/answer` does not exist, create it first. Write all final deliverables to `/root/answer/` and keep only the following results there:

- `/root/answer/observance_schedule.json`
  - Must contain the top-level keys: `program_name`, `year`, `selected_observances`, `rejected_observances`, `policy_summary`, `open_questions`
  - `year` must be `2026`
  - `selected_observances` must contain exactly 4 items
  - Each selected item must contain at least: `observance_id`, `title`, `lunar_rule`, `gregorian_date`, `weekday`, `audience_tag`, `format`, `evidence_id`

- `/root/answer/date_resolution.json`
  - Must contain the top-level keys: `year`, `resolutions`, `dataset_summary`, `cross_checks`
  - `resolutions` must cover every candidate observance from the catalog
  - Each resolution item must contain at least: `observance_id`, `lunar_rule`, `gregorian_date`, `weekday`, `resolution_status`, `cross_check_status`

- `/root/answer/source_audit.json`
  - Must contain the top-level keys: `source_checked`, `sources_used`, `evidence_records`, `notes`
  - `source_checked` must be a boolean, and the final result must set it to `true`
  - `evidence_records` must list the evidence filenames for the selected observances

- `/root/answer/selection_report.md`
  - The first line must be a one-sentence recommendation for the final 2026 program slate
  - Then write exactly 4 second-level headings, one for each selected observance, in chronological order
  - Each section must describe the chosen date, why it was selected, and any scheduling caution

- `/root/answer/evidence/`
  - Must contain supporting evidence records for the selected observances
  - Every selected observance must have one corresponding TSV evidence record in this directory
  - Name each evidence file `<observance_id>.tsv`
  - Each evidence file must keep the dataset header row and the matching source row for that selected observance

Notes:

- Use only the materials provided in the workspace.
- Keep the resolved dates consistent across all output files.
- Do not alter files outside `/root/answer/`.
- Do not change the candidate set, target year, or constraint definitions.
- Preserve enough support material for a reviewer to recheck every selected date.
