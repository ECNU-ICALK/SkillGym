You need to generate a 7-day onboarding plan for next week for a new member of a boutique fitness studio, to be delivered to the studio coach and nutrition advisor. The existing intake files and exported candidate exercise/food lists are already in the container, but they may be outdated or incomplete; the in-container planning service is the authoritative source for this delivery.

Input data is under `/root/data/`:

- `planner_manifest.json`: member id, planning window, delivery requirements, and the base URL of the local planning service.
- `member_profile.json`: member basics, goal phase, training experience, trainable days, allergens, disliked foods, exercise contraindications, and equipment restrictions.
- `equipment_inventory.csv`: currently available equipment in the studio, aliases, and allowed substitution groups.
- `meal_slot_rules.csv`: role constraints and minimum requirements for meal slots such as breakfast, lunch, pre-workout, post-workout, dinner, etc.
- `reference_exercise_shortlist.json`: an older export of candidate exercises; may be missing entries or outdated.
- `reference_food_shortlist.csv`: an older export of candidate foods; may be missing entries or outdated.

Your task

1. Complete a structured assessment for the member and derive the key metrics required by the training and nutrition plans.
2. Build 4 workout sessions for the member and cover all training days required in `member_profile.json`.
3. Create two reusable day-type meal plans for the member:
   - one `training_day`
   - one `rest_day`
4. Write an executable handoff summary for the studio coach.

Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/member_assessment.json`

The top-level structure must be exactly:

```json
{
  "member_id": "HF-001",
  "goal_phase": "cut",
  "bmi": 0.0,
  "bmr_kcal": 0.0,
  "tdee_kcal": 0.0,
  "training_day_kcal": 0.0,
  "rest_day_kcal": 0.0,
  "protein_g": 0.0,
  "fat_g": 0.0,
  "carbs_training_g": 0.0,
  "carbs_rest_g": 0.0,
  "fiber_target_g": 0.0
}
```

Requirements:

- All numeric fields must be numeric types.
- `goal_phase` must match the input.
- All numeric values must keep 2 decimal places.
- All fields must be derived from the current authoritative data and the member profile; do not leave fields empty or use placeholder values.

2. Write `/root/output/workout_plan.csv`

The column names must be exactly:

```csv
session_id,day_label,focus_block,exercise_id,exercise_name,primary_muscle,equipment_name,sets,reps_min,reps_max,rest_seconds,notes
```

Requirements:

- Must cover all training days required by `member_profile.json`.
- Each `session_id` must include at least 4 exercises.
- Only use exercises that exist and are still available in the current authoritative source.
- Only use equipment that is available in `equipment_inventory.csv` or an allowed substitute.
- Must comply with the member's injury limitations, contraindicated exercise keywords, and forbidden equipment restrictions.
- Must satisfy the training structure and scheduling requirements in the current program policy.
- `notes` must be a short note describing the purpose, constraints, or substitution context for the exercise.

3. Write `/root/output/meal_plan.csv`

The column names must be exactly:

```csv
day_type,meal_slot,food_id,food_name,grams,kcal,protein_g,carbs_g,fat_g,fiber_g
```

Requirements:

- `day_type` must be either `training_day` or `rest_day`.
- Both `day_type` values must appear.
- Every `meal_slot` must come from `meal_slot_rules.csv`.
- Only use foods that exist and are still available in the current authoritative source.
- Must follow the member's allergen and disliked-ingredient restrictions.
- Nutrition fields for each food row must match the selected food and the specified grams.
- All food grams must be a multiple of 5g.
- Do not evade constraints for any single meal slot by leaving it empty, deleting a meal slot, or renaming meal slots.
- The full-day totals for each `day_type` must fall within the tolerance specified by the current program policy.

4. Write `/root/output/coach_handoff.md`

The content must include the following top-level headings in this exact order:

- `# Client Goal`
- `# Assessment`
- `# Training Plan`
- `# Nutrition Plan`
- `# Risks And Substitutions`

Requirements:

- Must reference the key metrics consistent with `member_assessment.json`.
- Must summarize the actual plan consistent with `workout_plan.csv` and `meal_plan.csv`.
- Must explicitly list execution reminders, risks, and at least one practical exercise substitution or nutrition substitution.

Notes:

- The in-container planning service is the source of truth for this delivery.
- `reference_exercise_shortlist.json` and `reference_food_shortlist.csv` are older exports and are not the final system-of-record inputs.
- Do not modify any input files under `/root/data/`.
- Do not replace the real chain, do not bypass the local planning service, and do not use cached answers or manually fabricated outputs instead of the real planning process.
- Do not delete training days, delete meal slots, remove constraints, stop the service, or evade requirements by removing functionality.
- Do not substitute fictional exercises, fictional foods, or external website data in place of the local data chain.
- Do not modify tests, verifier, skill files, or environment files.
- You may write helper scripts in the working directory, but the only required deliverables are the 4 files under `/root/output/`.
