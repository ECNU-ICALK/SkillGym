You are assembling the meal operations packet for a three-day spring workshop. The event brief and pantry allowances are already in the workspace, and a synced Paprika workspace is available in the environment for the scheduled meals, recipe details, and grocery carryovers that apply during this run.

Input data is in `/root/data/`:

- `event_brief.json`: event id, service dates, guest count, meal slots, carryover policy, and per-person nutrition targets
- `pantry_allowance.csv`: pantry ingredients that may be deducted before any additional buying is planned

Your task

1. Read the scheduled workshop meals for every service date in `event_brief.json`.
2. Build the meal manifest for the scheduled lunch and dinner services, including the recipe identity and serving count for each slot.
3. Build the consolidated shopping delta after scaling every scheduled recipe to the workshop guest count and subtracting both pantry allowances and the reserved grocery carryovers that match the event policy in `event_brief.json`.
4. Audit the scheduled menu against the per-person daily nutrition targets in `event_brief.json`.
5. Prepare a short kitchen handoff for the workshop team.

Output

If `/root/output/` does not exist, create it first. Write only these files under `/root/output/`:

- `/root/output/meal_manifest.json`
  - Must contain top-level keys: `event_id`, `guest_count`, `service_dates`, `source_tool`, `meals`, `carryover_summary`, `manual_checks`
  - `service_dates` must keep the same order as `event_brief.json`
  - `source_tool` must be `"paprika"`
  - `meals` must contain exactly 6 objects, ordered by date and then by meal slot
  - Each meal object must contain: `date`, `meal_slot`, `recipe_uid`, `recipe_name`, `category`, `servings_planned`, `tags`, `total_time_min`, `source_ref`
  - `carryover_summary` must contain: `reserved_unpurchased_items`, `reserved_purchased_items`, `ignored_items`, `reserved_grams_total`
  - `manual_checks` must contain: `dates_complete`, `carryovers_applied`, `nutrition_checked`

- `/root/output/shopping_delta.csv`
  - Header must be exactly:
    `ingredient_id,ingredient_name,meal_dates,recipe_uids,required_grams,pantry_grams,carryover_grams,to_buy_grams`
  - Include one row per ingredient that still needs to be bought after pantry and carryover deductions
  - `meal_dates` must be a pipe-separated list of contributing service dates in ascending order
  - `recipe_uids` must be a pipe-separated list of contributing recipe UIDs in ascending order
  - Rows must be sorted by `ingredient_id` ascending

- `/root/output/nutrition_audit.json`
  - Must contain top-level keys: `event_id`, `per_day`, `overall`, `checks`
  - `per_day` must contain exactly 3 objects, one for each service date
  - Each `per_day` object must contain: `date`, `kcal_per_person`, `protein_g_per_person`, `carbs_g_per_person`, `fat_g_per_person`, `fiber_g_per_person`, `within_target`, `notes`
  - `overall` must contain: `planned_meals`, `unique_recipes`, `shopping_rows`
  - `checks` must contain: `protein_floor_met`, `fiber_floor_met`, `kcal_range_met`, `dates_complete`

- `/root/output/kitchen_notes.md`
  - Must contain these headings in this order:
    `# Meal Schedule`
    `# Carryover`
    `# Shopping Delta`
    `# Nutrition Watchpoints`
  - Must mention all scheduled recipe names
  - Must mention the carryover summary counts

Notes

- The Paprika workspace is the authority for scheduled meals, recipe details, and grocery carryovers during this run.
- Use the Paprika interface exposed in the workspace for schedule, recipe, and carryover lookup. Do not read its backing store files directly.
- Apply pantry and carryover deductions by exact `ingredient_id` only.
- Keep `/root/data/`, the Paprika workspace files, tests, and verifier files unchanged.
- Do not replace the meal schedule with a different set of meals.
- Do not add extra top-level outputs outside `/root/output/`.
- Final grading only checks the required files under `/root/output/`.
