from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
MANIFEST = json.loads((DATA_DIR / "planner_manifest.json").read_text(encoding="utf-8"))
SERVICE_URLS = MANIFEST["service_urls"]
PAGE_LIMIT = 4

ASSESSMENT_FIELDS = [
    "member_id",
    "goal_phase",
    "bmi",
    "bmr_kcal",
    "tdee_kcal",
    "training_day_kcal",
    "rest_day_kcal",
    "protein_g",
    "fat_g",
    "carbs_training_g",
    "carbs_rest_g",
    "fiber_target_g",
]

WORKOUT_COLUMNS = [
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
]

MEAL_COLUMNS = [
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
]


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "verifier-main"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paginate(url: str, params: dict[str, str]) -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    while True:
        query = dict(params)
        query["limit"] = str(PAGE_LIMIT)
        if cursor is not None:
            query["cursor"] = cursor
        payload = get_json(f"{url}?{urllib.parse.urlencode(query)}")
        items.extend(payload["items"])
        cursor = payload["page_info"]["next_cursor"]
        if cursor is None:
            return items


def round2(value: float) -> float:
    return round(value + 1e-9, 2)


def split_tags(raw: str) -> set[str]:
    return {part for part in raw.split(";") if part}


def load_output_json(name: str) -> dict:
    return json.loads((OUTPUT_DIR / name).read_text(encoding="utf-8"))


def load_output_csv(name: str) -> list[dict]:
    with (OUTPUT_DIR / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def member_profile() -> dict:
    return json.loads((DATA_DIR / "member_profile.json").read_text(encoding="utf-8"))


def equipment_inventory() -> dict[str, dict]:
    with (DATA_DIR / "equipment_inventory.csv").open(newline="", encoding="utf-8") as fh:
        return {row["equipment_id"]: row for row in csv.DictReader(fh)}


def meal_slot_rules() -> dict[tuple[str, str], dict]:
    with (DATA_DIR / "meal_slot_rules.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {(row["day_type"], row["meal_slot"]): row for row in rows}


def policy() -> dict:
    return get_json(SERVICE_URLS["policy_current"])


def exercise_catalog() -> dict[str, dict]:
    rows = paginate(SERVICE_URLS["exercise_catalog"], {"approved": "true", "language": "en"})
    return {row["exercise_id"]: row for row in rows}


def food_catalog() -> dict[str, dict]:
    rows = paginate(SERVICE_URLS["food_catalog"], {"edible": "true", "language": "en"})
    return {row["food_id"]: row for row in rows}


def expected_assessment() -> dict:
    member = member_profile()
    rules = policy()["assessment_rules"]
    weight = float(member["weight_kg"])
    height_cm = float(member["height_cm"])
    height_m = height_cm / 100.0
    age = float(member["age_years"])

    bmi = weight / (height_m ** 2)
    if member["sex"] == "male":
        bmr = 10.0 * weight + 6.25 * height_cm - 5.0 * age + 5.0
    else:
        bmr = 10.0 * weight + 6.25 * height_cm - 5.0 * age - 161.0

    activity_factor = float(rules["activity_factors"][member["activity_level"]])
    tdee = bmr * activity_factor
    phase = rules["phase_calorie_adjustments"][member["goal_phase"]]
    training_day_kcal = tdee + float(phase["training_day_delta_kcal"])
    rest_day_kcal = tdee + float(phase["rest_day_delta_kcal"])
    protein_g = weight * float(rules["protein_g_per_kg"])
    fat_g = weight * float(rules["fat_g_per_kg"])
    carbs_training_g = (training_day_kcal - protein_g * 4.0 - fat_g * 9.0) / 4.0
    carbs_rest_g = (rest_day_kcal - protein_g * 4.0 - fat_g * 9.0) / 4.0

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
        "fiber_target_g": round2(float(rules["fiber_target_g"])),
    }


def compute_day_totals(rows: list[dict]) -> dict[str, dict[str, float]]:
    totals = defaultdict(lambda: {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0})
    for row in rows:
        bucket = totals[row["day_type"]]
        for key in ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]:
            bucket[key] += float(row[key])
    return totals


def compute_slot_totals(rows: list[dict]) -> dict[tuple[str, str], dict[str, float]]:
    totals = defaultdict(lambda: {"foods": 0, "protein_g": 0.0, "fat_g": 0.0})
    for row in rows:
        key = (row["day_type"], row["meal_slot"])
        totals[key]["foods"] += 1
        totals[key]["protein_g"] += float(row["protein_g"])
        totals[key]["fat_g"] += float(row["fat_g"])
    return totals


def test_required_output_files_exist() -> None:
    for filename in ["member_assessment.json", "workout_plan.csv", "meal_plan.csv", "coach_handoff.md"]:
        assert (OUTPUT_DIR / filename).exists(), f"Missing required output file: {filename}"


def test_member_assessment_schema_and_values() -> None:
    payload = load_output_json("member_assessment.json")
    expected = expected_assessment()
    assert list(payload.keys()) == ASSESSMENT_FIELDS, "member_assessment.json fields do not match the required schema"
    assert payload["member_id"] == expected["member_id"]
    assert payload["goal_phase"] == expected["goal_phase"]
    for key in ASSESSMENT_FIELDS[2:]:
        assert isinstance(payload[key], (int, float)), f"{key} must be numeric"
        assert abs(float(payload[key]) - expected[key]) <= 0.01, f"Incorrect value for {key}"
        assert round(float(payload[key]), 2) == float(payload[key]), f"{key} must keep 2 decimals"


def test_workout_plan_meets_live_constraints() -> None:
    rows = load_output_csv("workout_plan.csv")
    assert rows, "workout_plan.csv is empty"
    assert list(rows[0].keys()) == WORKOUT_COLUMNS, "workout_plan.csv columns do not match the required schema"

    member = member_profile()
    rules = policy()["training_rules"]
    exercises = exercise_catalog()
    equipment = equipment_inventory()
    required_days = set(member["available_training_days"])
    banned_tags = set(member["prohibited_movement_tags"])
    banned_equipment = set(member["banned_equipment_ids"])
    category_rules = rules["category_rules"]

    session_rows = defaultdict(list)
    weekly_sets = defaultdict(int)

    for row in rows:
        assert row["day_label"] in required_days, f"Unexpected training day: {row['day_label']}"
        assert row["focus_block"] == rules["required_focus_blocks_by_day"][row["day_label"]], f"Unexpected focus block for {row['day_label']}"
        exercise = exercises[row["exercise_id"]]
        assert row["exercise_name"] == exercise["exercise_name"]
        assert row["primary_muscle"] == exercise["primary_muscle"]
        assert row["equipment_name"] == exercise["equipment_name"]
        assert exercise["approved"] is True
        assert exercise["language"] in rules["exercise_filters"]["allowed_languages"]
        assert not (set(exercise["movement_tags"]) & banned_tags), f"{row['exercise_id']} violates prohibited movement tags"
        assert exercise["equipment_id"] not in banned_equipment, f"{row['exercise_id']} uses banned equipment"
        assert equipment[exercise["equipment_id"]]["available"] == "true", f"{row['exercise_id']} uses unavailable equipment"

        bounds = category_rules[exercise["category"]]
        sets = int(row["sets"])
        reps_min = int(row["reps_min"])
        reps_max = int(row["reps_max"])
        rest_seconds = int(row["rest_seconds"])
        assert bounds["sets_min"] <= sets <= bounds["sets_max"]
        assert bounds["reps_min"] <= reps_min <= reps_max <= bounds["reps_max"]
        assert bounds["rest_seconds_min"] <= rest_seconds <= bounds["rest_seconds_max"]
        assert row["notes"].strip()

        session_rows[row["session_id"]].append(row)
        weekly_sets[exercise["primary_muscle"]] += sets

    assert len(session_rows) == int(rules["required_sessions"])
    covered_days = {bucket[0]["day_label"] for bucket in session_rows.values()}
    assert covered_days == required_days

    for bucket in session_rows.values():
        assert len(bucket) >= int(rules["minimum_exercises_per_session"])
        assert len({row["exercise_id"] for row in bucket}) == len(bucket)
        assert len({row["day_label"] for row in bucket}) == 1
        assert len({row["focus_block"] for row in bucket}) == 1
        compounds = sum(1 for row in bucket if exercises[row["exercise_id"]]["category"] == "compound")
        accessories = sum(1 for row in bucket if exercises[row["exercise_id"]]["category"] == "accessory")
        assert compounds >= int(rules["minimum_compound_exercises_per_session"])
        assert accessories >= int(rules["minimum_accessory_exercises_per_session"])

    for muscle, minimum_sets in rules["weekly_primary_muscle_set_targets"].items():
        assert weekly_sets[muscle] >= int(minimum_sets), f"Weekly set target not met for {muscle}"


def test_meal_plan_meets_live_constraints() -> None:
    rows = load_output_csv("meal_plan.csv")
    assert rows, "meal_plan.csv is empty"
    assert list(rows[0].keys()) == MEAL_COLUMNS, "meal_plan.csv columns do not match the required schema"

    member = member_profile()
    rules = policy()["meal_rules"]
    foods = food_catalog()
    slot_rules = meal_slot_rules()
    assessment = load_output_json("member_assessment.json")
    present_slots = defaultdict(set)
    disallowed_allergens = set(member["disallowed_allergens"])
    avoid_tags = set(member["avoid_food_tags"])

    for row in rows:
        key = (row["day_type"], row["meal_slot"])
        assert key in slot_rules, f"Unexpected meal slot: {key}"
        food = foods[row["food_id"]]
        assert row["food_name"] == food["food_name"]
        assert food["edible"].lower() == "true"
        assert row["food_id"] not in set(member["avoid_food_ids"])
        assert not (split_tags(food["allergens"]) & disallowed_allergens)
        assert not (split_tags(food["avoid_tags"]) & avoid_tags)
        assert row["meal_slot"] in split_tags(food["slot_tags"])

        grams = int(row["grams"])
        assert grams > 0
        assert grams % int(rules["grams_increment"]) == 0

        factor = grams / 100.0
        expected = {
            "kcal": round2(float(food["kcal_per_100g"]) * factor),
            "protein_g": round2(float(food["protein_g_per_100g"]) * factor),
            "carbs_g": round2(float(food["carbs_g_per_100g"]) * factor),
            "fat_g": round2(float(food["fat_g_per_100g"]) * factor),
            "fiber_g": round2(float(food["fiber_g_per_100g"]) * factor),
        }
        for nutrient, value in expected.items():
            assert abs(float(row[nutrient]) - value) <= 0.01, f"Incorrect {nutrient} for {row['food_id']}"
        present_slots[row["day_type"]].add(row["meal_slot"])

    for day_type, required_slots in rules["required_slots"].items():
        assert present_slots[day_type] == set(required_slots)

    slot_totals = compute_slot_totals(rows)
    for key, rule in slot_rules.items():
        totals = slot_totals[key]
        assert int(rule["min_foods"]) <= totals["foods"] <= int(rule["max_foods"])
        assert totals["protein_g"] + 1e-9 >= float(rule["min_protein_g"])
        assert totals["fat_g"] <= float(rule["max_fat_g"]) + 1e-9

    totals = compute_day_totals(rows)
    kcal_tol = float(rules["kcal_tolerance"])
    macro_tol = float(rules["macro_tolerance_g"])
    fiber_tol = float(rules["fiber_tolerance_g"])
    assert abs(totals["training_day"]["kcal"] - float(assessment["training_day_kcal"])) <= kcal_tol
    assert abs(totals["rest_day"]["kcal"] - float(assessment["rest_day_kcal"])) <= kcal_tol
    assert abs(totals["training_day"]["protein_g"] - float(assessment["protein_g"])) <= macro_tol
    assert abs(totals["rest_day"]["protein_g"] - float(assessment["protein_g"])) <= macro_tol
    assert abs(totals["training_day"]["fat_g"] - float(assessment["fat_g"])) <= macro_tol
    assert abs(totals["rest_day"]["fat_g"] - float(assessment["fat_g"])) <= macro_tol
    assert abs(totals["training_day"]["carbs_g"] - float(assessment["carbs_training_g"])) <= macro_tol
    assert abs(totals["rest_day"]["carbs_g"] - float(assessment["carbs_rest_g"])) <= macro_tol
    assert abs(totals["training_day"]["fiber_g"] - float(assessment["fiber_target_g"])) <= fiber_tol
    assert abs(totals["rest_day"]["fiber_g"] - float(assessment["fiber_target_g"])) <= fiber_tol


def test_handoff_matches_plan() -> None:
    text = (OUTPUT_DIR / "coach_handoff.md").read_text(encoding="utf-8")
    member = member_profile()
    handoff_rules = policy()["handoff_rules"]
    assessment = load_output_json("member_assessment.json")
    workout_rows = load_output_csv("workout_plan.csv")
    meal_rows = load_output_csv("meal_plan.csv")
    positions = []
    for heading in handoff_rules["required_headings"]:
        pos = text.find(heading)
        assert pos != -1, f"Missing required heading: {heading}"
        positions.append(pos)
    assert positions == sorted(positions)
    lower_text = text.lower()
    assert member["client_name"].lower() in lower_text or member["member_id"].lower() in lower_text
    assert member["goal_phase"] in lower_text or "cutting" in lower_text
    assert "swap" in lower_text or "substitut" in lower_text
    assert str(int(round(float(assessment["training_day_kcal"])))) in text
    assert str(int(round(float(assessment["rest_day_kcal"])))) in text
    assert sum(1 for name, _ in Counter(row["exercise_name"] for row in workout_rows).most_common(3) if name.lower() in lower_text) >= 2
    assert sum(1 for name, _ in Counter(row["food_name"] for row in meal_rows).most_common(4) if any(token in lower_text for token in name.lower().split()[:2])) >= 2
    assert sum(1 for tag in member["prohibited_movement_tags"] if tag.replace("_", " ") in lower_text) >= 1
