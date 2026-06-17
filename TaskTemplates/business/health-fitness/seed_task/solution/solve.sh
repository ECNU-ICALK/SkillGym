#!/bin/bash
set -euo pipefail

OUTPUT_DIR_PATH="${OUTPUT_DIR:-/root/output}"
mkdir -p "$OUTPUT_DIR_PATH"
if command -v start-health-fitness-planner >/dev/null 2>&1; then
  start-health-fitness-planner
fi

python3 - <<'PY'
from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "oracle-solve"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paginate(url: str, params: dict[str, str]) -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    while True:
        query = dict(params)
        if cursor is not None:
            query["cursor"] = cursor
        payload = get_json(f"{url}?{urllib.parse.urlencode(query)}")
        items.extend(payload["items"])
        cursor = payload["page_info"]["next_cursor"]
        if cursor is None:
            return items


def round2(value: float) -> float:
    return round(value + 1e-9, 2)


manifest = load_json(DATA_DIR / "planner_manifest.json")
member = load_json(DATA_DIR / "member_profile.json")
policy = get_json(manifest["service_urls"]["policy_current"])
exercise_catalog = {
    row["exercise_id"]: row
    for row in paginate(manifest["service_urls"]["exercise_catalog"], {"approved": "true", "language": "en", "limit": "4"})
}
food_catalog = {
    row["food_id"]: row
    for row in paginate(manifest["service_urls"]["food_catalog"], {"edible": "true", "language": "en", "limit": "4"})
}


def build_assessment() -> dict:
    weight = float(member["weight_kg"])
    height_cm = float(member["height_cm"])
    age = float(member["age_years"])
    height_m = height_cm / 100.0
    bmi = weight / (height_m ** 2)
    if member["sex"] == "male":
        bmr = 10.0 * weight + 6.25 * height_cm - 5.0 * age + 5.0
    else:
        bmr = 10.0 * weight + 6.25 * height_cm - 5.0 * age - 161.0
    activity = policy["assessment_rules"]["activity_factors"][member["activity_level"]]
    tdee = bmr * activity
    phase = policy["assessment_rules"]["phase_calorie_adjustments"][member["goal_phase"]]
    training_day_kcal = tdee + phase["training_day_delta_kcal"]
    rest_day_kcal = tdee + phase["rest_day_delta_kcal"]
    protein_g = weight * float(policy["assessment_rules"]["protein_g_per_kg"])
    fat_g = weight * float(policy["assessment_rules"]["fat_g_per_kg"])
    carbs_training_g = (training_day_kcal - protein_g * 4.0 - fat_g * 9.0) / 4.0
    carbs_rest_g = (rest_day_kcal - protein_g * 4.0 - fat_g * 9.0) / 4.0
    fiber_target_g = float(policy["assessment_rules"]["fiber_target_g"])
    return {
        "member_id": member["member_id"],
        "goal_phase": member["goal_phase"],
        "bmi": round2(bmi),
        "bmr_kcal": round2(bmr),
        "tdee_kcal": round2(tdee),
        "training_day_kcal": round2(training_day_kcal),
        "rest_day_kcal": round2(rest_day_kcal),
        "protein_g": round2(protein_g),
        "fat_g": round2(fat_g),
        "carbs_training_g": round2(carbs_training_g),
        "carbs_rest_g": round2(carbs_rest_g),
        "fiber_target_g": round2(fiber_target_g),
    }


assessment = build_assessment()

workout_rows = [
    {"session_id": "S1", "day_label": "Monday", "focus_block": "upper_a", "exercise_id": "EX001", "sets": 4, "reps_min": 6, "reps_max": 10, "rest_seconds": 120, "notes": "Primary chest press that avoids vertical pressing stress."},
    {"session_id": "S1", "day_label": "Monday", "focus_block": "upper_a", "exercise_id": "EX002", "sets": 4, "reps_min": 8, "reps_max": 10, "rest_seconds": 120, "notes": "Supported row keeps back volume high with low setup cost."},
    {"session_id": "S1", "day_label": "Monday", "focus_block": "upper_a", "exercise_id": "EX010", "sets": 3, "reps_min": 10, "reps_max": 12, "rest_seconds": 75, "notes": "Unilateral cable row adds extra horizontal-pull volume."},
    {"session_id": "S1", "day_label": "Monday", "focus_block": "upper_a", "exercise_id": "EX004", "sets": 3, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Shoulder isolation that keeps overhead loading out of the plan."},
    {"session_id": "S2", "day_label": "Tuesday", "focus_block": "lower_a", "exercise_id": "EX005", "sets": 4, "reps_min": 8, "reps_max": 10, "rest_seconds": 120, "notes": "Box target limits knee depth while maintaining quad work."},
    {"session_id": "S2", "day_label": "Tuesday", "focus_block": "lower_a", "exercise_id": "EX006", "sets": 4, "reps_min": 8, "reps_max": 10, "rest_seconds": 120, "notes": "Hip hinge emphasis supports hamstrings without deep knee flexion."},
    {"session_id": "S2", "day_label": "Tuesday", "focus_block": "lower_a", "exercise_id": "EX007", "sets": 3, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Machine curl adds knee-flexion volume without loading the back."},
    {"session_id": "S2", "day_label": "Tuesday", "focus_block": "lower_a", "exercise_id": "EX008", "sets": 3, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Bridge pattern keeps glute work simple and repeatable."},
    {"session_id": "S3", "day_label": "Thursday", "focus_block": "upper_b", "exercise_id": "EX009", "sets": 4, "reps_min": 6, "reps_max": 10, "rest_seconds": 120, "notes": "Second chest-press angle for weekly pressing volume."},
    {"session_id": "S3", "day_label": "Thursday", "focus_block": "upper_b", "exercise_id": "EX003", "sets": 3, "reps_min": 8, "reps_max": 10, "rest_seconds": 105, "notes": "Vertical pull completes the upper-body movement split."},
    {"session_id": "S3", "day_label": "Thursday", "focus_block": "upper_b", "exercise_id": "EX011", "sets": 3, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Rear-delt work supports shoulder tolerance and posture."},
    {"session_id": "S3", "day_label": "Thursday", "focus_block": "upper_b", "exercise_id": "EX004", "sets": 3, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Repeat lateral-raise slot keeps shoulder volume high without overhead pressing."},
    {"session_id": "S4", "day_label": "Saturday", "focus_block": "lower_b", "exercise_id": "EX012", "sets": 3, "reps_min": 8, "reps_max": 10, "rest_seconds": 120, "notes": "Partial-range leg press is the safe squat-pattern substitute when knees flare up."},
    {"session_id": "S4", "day_label": "Saturday", "focus_block": "lower_b", "exercise_id": "EX006", "sets": 3, "reps_min": 8, "reps_max": 10, "rest_seconds": 120, "notes": "Second hinge exposure keeps posterior-chain loading simple."},
    {"session_id": "S4", "day_label": "Saturday", "focus_block": "lower_b", "exercise_id": "EX013", "sets": 3, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Cable pull-through provides the glute-bias slot required for the week."},
    {"session_id": "S4", "day_label": "Saturday", "focus_block": "lower_b", "exercise_id": "EX007", "sets": 2, "reps_min": 12, "reps_max": 15, "rest_seconds": 60, "notes": "Short extra hamstring slot tops up weekly posterior-chain volume."}
]

for row in workout_rows:
    exercise = exercise_catalog[row["exercise_id"]]
    row["exercise_name"] = exercise["exercise_name"]
    row["primary_muscle"] = exercise["primary_muscle"]
    row["equipment_name"] = exercise["equipment_name"]

with (OUTPUT_DIR / "workout_plan.csv").open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "session_id",
            "day_label",
            "focus_block",
            "exercise_id",
            "exercise_name",
            "primary_muscle",
            "equipment_name",
            "sets",
            "reps_min",
            "reps_max",
            "rest_seconds",
            "notes",
        ],
    )
    writer.writeheader()
    writer.writerows(workout_rows)


meal_rows = [
    ("training_day", "breakfast", "FOOD001", 35),
    ("training_day", "breakfast", "FOOD002", 200),
    ("training_day", "breakfast", "FOOD003", 80),
    ("training_day", "lunch", "FOOD004", 130),
    ("training_day", "lunch", "FOOD005", 100),
    ("training_day", "lunch", "FOOD006", 100),
    ("training_day", "lunch", "FOOD007", 15),
    ("training_day", "pre_workout", "FOOD008", 80),
    ("training_day", "pre_workout", "FOOD009", 20),
    ("training_day", "post_workout", "FOOD010", 250),
    ("training_day", "post_workout", "FOOD003", 70),
    ("training_day", "dinner", "FOOD011", 180),
    ("training_day", "dinner", "FOOD015", 100),
    ("training_day", "dinner", "FOOD006", 100),
    ("training_day", "dinner", "FOOD016", 70),
    ("rest_day", "breakfast", "FOOD001", 35),
    ("rest_day", "breakfast", "FOOD002", 180),
    ("rest_day", "breakfast", "FOOD003", 80),
    ("rest_day", "lunch", "FOOD004", 120),
    ("rest_day", "lunch", "FOOD005", 40),
    ("rest_day", "lunch", "FOOD006", 100),
    ("rest_day", "lunch", "FOOD007", 10),
    ("rest_day", "lunch", "FOOD016", 50),
    ("rest_day", "snack", "FOOD010", 250),
    ("rest_day", "snack", "FOOD008", 70),
    ("rest_day", "snack", "FOOD017", 15),
    ("rest_day", "dinner", "FOOD011", 180),
    ("rest_day", "dinner", "FOOD015", 120),
    ("rest_day", "dinner", "FOOD006", 100),
    ("rest_day", "dinner", "FOOD007", 5)
]

meal_output = []
for day_type, meal_slot, food_id, grams in meal_rows:
    food = food_catalog[food_id]
    factor = grams / 100.0
    meal_output.append({
        "day_type": day_type,
        "meal_slot": meal_slot,
        "food_id": food_id,
        "food_name": food["food_name"],
        "grams": str(grams),
        "kcal": f"{round2(float(food['kcal_per_100g']) * factor):.2f}",
        "protein_g": f"{round2(float(food['protein_g_per_100g']) * factor):.2f}",
        "carbs_g": f"{round2(float(food['carbs_g_per_100g']) * factor):.2f}",
        "fat_g": f"{round2(float(food['fat_g_per_100g']) * factor):.2f}",
        "fiber_g": f"{round2(float(food['fiber_g_per_100g']) * factor):.2f}",
    })

with (OUTPUT_DIR / "meal_plan.csv").open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "day_type",
            "meal_slot",
            "food_id",
            "food_name",
            "grams",
            "kcal",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
        ],
    )
    writer.writeheader()
    writer.writerows(meal_output)

with (OUTPUT_DIR / "member_assessment.json").open("w", encoding="utf-8") as fh:
    json.dump(assessment, fh, indent=2)

handoff = f"""# Client Goal
Maya Chen is starting a 7-day cutting phase with four gym sessions on Monday, Tuesday, Thursday, and Saturday. Keep execution simple, protect the knee and shoulder, and keep the plan close to the training-day target of {assessment['training_day_kcal']:.2f} kcal and rest-day target of {assessment['rest_day_kcal']:.2f} kcal.

# Assessment
Current assessment: BMI {assessment['bmi']:.2f}, BMR {assessment['bmr_kcal']:.2f} kcal, and TDEE {assessment['tdee_kcal']:.2f} kcal. Protein stays high at {assessment['protein_g']:.2f} g daily, fats stay near {assessment['fat_g']:.2f} g, carbs cycle from {assessment['carbs_training_g']:.2f} g on training days to {assessment['carbs_rest_g']:.2f} g on rest days, and fiber stays anchored near {assessment['fiber_target_g']:.2f} g.

# Training Plan
Upper days center on Dumbbell Bench Press, Chest Supported Cable Row, Single Arm Cable Row, Lat Pulldown, Cable Lateral Raise, Incline Dumbbell Bench Press, and Reverse Pec Deck Fly. Lower days center on Goblet Box Squat, Dumbbell Romanian Deadlift, Seated Leg Curl, Glute Bridge, Leg Press Partial Range, and Cable Pull Through. If the cable row station is occupied, swap Chest Supported Cable Row for Single Arm Cable Row; if knee symptoms rise, swap Goblet Box Squat for Leg Press Partial Range.

# Nutrition Plan
Training days use oats, egg whites, blueberries, chicken breast, jasmine rice, banana, rice cakes, lactose-free Greek Yogurt, strawberries, salmon, sweet potato, spinach, and avocado to keep carbs around sessions. Rest days lower carbs by reducing rice and banana portions while keeping protein anchored with chicken, salmon, yogurt, and egg whites. Olive oil and avocado keep fats steady without relying on whey, cottage cheese, tuna, or shellfish.

# Risks And Substitutions
Main risks are deep knee flexion aggravating the knee, vertical overhead press aggravating the shoulder, and drifting toward convenience foods she avoids. Keep the barbell, hack squat, and overhead pressing patterns out of the plan. If the cable station is busy on Saturday, swap Cable Pull Through for Glute Bridge volume, and if post-workout strawberries are unavailable, swap in a matched-carb portion of blueberries or banana while keeping the same total grams strategy.
"""

(OUTPUT_DIR / "coach_handoff.md").write_text(handoff, encoding="utf-8")
PY
