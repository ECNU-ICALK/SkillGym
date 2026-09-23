You are preparing a release package for an offline aqueous-solubility benchmark.

Input data is available in `/root/workspace/data/`:

- `train.csv`: labeled training split
- `valid.csv`: labeled validation split
- `test.csv`: labeled test split
- `holdout.csv`: unlabeled release split
- `project_rules.json`: current release rules, selection logic, exclusion rules, and retention limits
- `reference_baseline.json`: earlier benchmark snapshot kept for comparison
- `project_brief.md`: handoff notes for this release

A local experiment workspace is available in `/root/workspace/workbench/`.

Your task:

1. Prepare a current release package from the provided data, the local experiment workspace, and the current rules in `project_rules.json`.
2. Review the existing experiment snapshot and add any current run needed for the release package.
3. Compare the current candidate model families required by the bundled rules before final selection.
4. Assess the workspace footprint before and after retention handling, and keep that review in the release notes.
5. Review the selected retained run details from the workspace before generating the final package.
6. Identify invalid or duplicate molecular rows, exclude them from scored artifacts, and preserve a clear audit trail.
7. Select one final model using the current release rules. The selected model must come from the local experiment workspace and must remain retained after any workspace cleanup required by the project rules.
8. Generate predictions for the scored and holdout splits with the selected model.
9. Write the following files under `/root/workspace/output/`:
   - `model_summary.csv`
   - `selected_model.json`
   - `test_predictions.csv`
   - `holdout_predictions.csv`
   - `excluded_rows.csv`
   - `method_notes.md`

Output requirements:

- `model_summary.csv` must contain these columns exactly:

```text
rank,run_id,selection_status,valid_rmse,valid_mae,test_rmse,test_mae,train_rows,valid_rows,test_rows,notes
```

- `selected_model.json` must contain these top-level fields:

```json
{
  "task": "...",
  "selected_run_id": "...",
  "selection_metric": "...",
  "metrics": {},
  "artifacts": {},
  "summary": {}
}
```

- `test_predictions.csv` must contain these columns exactly:

```text
row_id,smiles,measured_logS,predicted_logS,residual,used_for_scoring
```

- `holdout_predictions.csv` must contain these columns exactly:

```text
row_id,smiles,predicted_logS
```

- `excluded_rows.csv` must contain these columns exactly:

```text
source_file,row_id,smiles,reason
```

- `method_notes.md` must briefly describe the release process used in this run, including row exclusions, footprint review before and after retention handling, final-model selection, retained-run review, and output generation.

Additional requirements:

- `rank` must start at `1` and increase consecutively.
- `model_summary.csv` must include one row for each run that remains retained in the local experiment workspace after cleanup. Do not include removed runs.
- `selection_status` must use one of the following values:
  - `selected`
  - `eligible`
  - `rejected`
- `predicted_logS`, `valid_rmse`, `valid_mae`, `test_rmse`, and `test_mae` must be numeric.
- `used_for_scoring` must be either `true` or `false`.
- All CSV outputs must include headers.
- All JSON outputs must be valid UTF-8 JSON.

Notes:

- You may use reasonable open-source Python packages and the local experiment workspace.
- Base the release package on the current bundled data and current bundled rules.
- Use the existing local workspace tooling and workspace records as the control surface for this release package.
- Standalone replacement workflow code that bypasses the local workspace tooling is not allowed.
- Hardcoded rankings, copied outputs, fabricated metrics, and placeholder prediction values are not allowed.
- Do not modify input data, tests, runtime wiring, or the skill files.
