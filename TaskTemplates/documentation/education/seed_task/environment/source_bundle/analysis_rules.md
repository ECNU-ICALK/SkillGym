# Analysis Rules

1. Build one long-format indicator table with these canonical indicator names only:
   - `mean_years_schooling`
   - `gross_upper_secondary_enrolment_pct`
   - `education_spending_pct_gdp`
2. Use only entities listed in `country_cohort.csv` where `include_in_lesson = yes`.
3. For the final exported cohort table, keep only years 2018 through 2022 inclusive.
4. Compute `latest_common_year` after filtering to the included cohort and required indicators. It must be the maximum year shared by every included entity across all three indicators.
5. Round exported numeric values in `cohort_indicator_table.csv` and `lesson_summary.json` to 2 decimals.
6. Sort `cohort_indicator_table.csv` by `entity`, `indicator`, then `year`, all ascending.
7. `lesson_summary.json` must contain at least 3 takeaways. Each takeaway must cite at least 2 evidence rows from the exported cohort table.
8. Same-year comparisons in the takeaways must use `latest_common_year`. Trend commentary may refer to 2018-2022 patterns, but it must still cite values present in the exported table.
9. Keep the notebook descriptive and evidence-bound. Do not add outside metrics, policy prescriptions, or causal explanations.
