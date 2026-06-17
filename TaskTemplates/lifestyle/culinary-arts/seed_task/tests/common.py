import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
PAPRIKA_DATA_DIR = Path(os.environ.get("PAPRIKA_DATA_DIR", "/opt/paprika_store"))
SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", "/logs/agent/skills"))
ACCESS_LOG = Path(os.environ.get("PAPRIKA_ACCESS_LOG", "/var/log/paprika_access.log"))
CHECKSUM_DIR = Path(os.environ.get("CHECKSUM_DIR", "/opt"))
CLI_PATH = Path(os.environ.get("PAPRIKA_CLI_PATH", "/opt/internal_tools/mealops"))

EXPECTED_OUTPUT_FILES = {
    "meal_manifest.json",
    "shopping_delta.csv",
    "nutrition_audit.json",
    "kitchen_notes.md",
}

SHOPPING_COLUMNS = [
    "ingredient_id",
    "ingredient_name",
    "meal_dates",
    "recipe_uids",
    "required_grams",
    "pantry_grams",
    "carryover_grams",
    "to_buy_grams",
]


def read_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checksum_manifest(path, exclude_prefixes=()):
    lines = []
    for file_path in sorted(Path(path).rglob("*")):
        if file_path.is_file():
            rel = file_path.relative_to(path)
            if exclude_prefixes and any(rel.as_posix().startswith(prefix) for prefix in exclude_prefixes):
                continue
            lines.append(f"{hash_file(file_path)}  ./{rel.as_posix()}")
    return "\n".join(lines) + ("\n" if lines else "")


def read_recipe_data():
    recipes = read_json(PAPRIKA_DATA_DIR / "recipes.json")
    meals = read_json(PAPRIKA_DATA_DIR / "meals.json")
    groceries = read_json(PAPRIKA_DATA_DIR / "groceries.json")
    return recipes, meals, groceries


def expected_outputs():
    brief = read_json(DATA_DIR / "event_brief.json")
    pantry_rows = read_csv(DATA_DIR / "pantry_allowance.csv")
    recipes, scheduled_meals, groceries = read_recipe_data()
    pantry = {row["ingredient_id"]: float(row["grams_available"]) for row in pantry_rows}
    recipes_by_uid = {row["uid"]: row for row in recipes}

    meals = []
    recipe_cache = {}
    for service_date in brief["service_dates"]:
        date_meals = [row for row in scheduled_meals if row["date"] == service_date]
        for slot in brief["meal_slots"]:
            scheduled = next(row for row in date_meals if row["meal_type"] == slot)
            recipe = recipes_by_uid[scheduled["recipe_uid"]]
            recipe_cache[recipe["uid"]] = recipe
            meals.append(
                {
                    "date": service_date,
                    "meal_slot": slot,
                    "recipe_uid": recipe["uid"],
                    "recipe_name": recipe["name"],
                    "category": recipe["category"],
                    "servings_planned": brief["guest_count"],
                    "tags": recipe["tags"],
                    "total_time_min": recipe["total_time_min"],
                    "source_ref": f"paprika:{recipe['uid']}",
                }
            )

    carryover_key = brief["carryover_policy"]["reserved_event_field"]
    carryover_value = brief["carryover_policy"]["matching_value"]
    carryover_by_ingredient = defaultdict(float)
    reserved_unpurchased = 0
    reserved_purchased = 0
    ignored_items = 0
    reserved_total_grams = 0.0
    for row in groceries:
        if row.get(carryover_key) == carryover_value:
            carryover_by_ingredient[row["ingredient_id"]] += float(row["grams"])
            reserved_total_grams += float(row["grams"])
            if row["purchased"]:
                reserved_purchased += 1
            else:
                reserved_unpurchased += 1
        else:
            ignored_items += 1

    consolidated = {}
    daily_nutrition = defaultdict(lambda: {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0})
    for meal in meals:
        recipe = recipe_cache[meal["recipe_uid"]]
        scale = brief["guest_count"] / recipe["servings"]
        for item in recipe["ingredients"]:
            bucket = consolidated.setdefault(
                item["ingredient_id"],
                {
                    "ingredient_name": item["ingredient_name"],
                    "meal_dates": set(),
                    "recipe_uids": set(),
                    "required_grams": 0.0,
                },
            )
            bucket["meal_dates"].add(meal["date"])
            bucket["recipe_uids"].add(meal["recipe_uid"])
            bucket["required_grams"] += float(item["grams"]) * scale
        nutrition = recipe["nutrition_per_serving"]
        day_bucket = daily_nutrition[meal["date"]]
        day_bucket["kcal"] += float(nutrition["kcal"])
        day_bucket["protein"] += float(nutrition["protein_g"])
        day_bucket["carbs"] += float(nutrition["carbs_g"])
        day_bucket["fat"] += float(nutrition["fat_g"])
        day_bucket["fiber"] += float(nutrition["fiber_g"])

    shopping_rows = []
    for ingredient_id in sorted(consolidated):
        row = consolidated[ingredient_id]
        pantry_grams = pantry.get(ingredient_id, 0.0)
        carryover_grams = carryover_by_ingredient.get(ingredient_id, 0.0)
        to_buy = row["required_grams"] - pantry_grams - carryover_grams
        if to_buy <= 0:
            continue
        shopping_rows.append(
            {
                "ingredient_id": ingredient_id,
                "ingredient_name": row["ingredient_name"],
                "meal_dates": "|".join(sorted(row["meal_dates"])),
                "recipe_uids": "|".join(sorted(row["recipe_uids"])),
                "required_grams": f"{row['required_grams']:.1f}",
                "pantry_grams": f"{pantry_grams:.1f}",
                "carryover_grams": f"{carryover_grams:.1f}",
                "to_buy_grams": f"{to_buy:.1f}",
            }
        )

    checks = {
        "protein_floor_met": True,
        "fiber_floor_met": True,
        "kcal_range_met": True,
        "dates_complete": True,
    }
    per_day = []
    for service_date in brief["service_dates"]:
        totals = daily_nutrition[service_date]
        within_target = True
        notes = []
        if totals["protein"] < brief["nutrition_targets_per_person"]["protein_min_g"]:
            checks["protein_floor_met"] = False
            within_target = False
            notes.append("protein below floor")
        if totals["fiber"] < brief["nutrition_targets_per_person"]["fiber_min_g"]:
            checks["fiber_floor_met"] = False
            within_target = False
            notes.append("fiber below floor")
        if totals["kcal"] < brief["nutrition_targets_per_person"]["kcal_min"] or totals["kcal"] > brief["nutrition_targets_per_person"]["kcal_max"]:
            checks["kcal_range_met"] = False
            within_target = False
            notes.append("kcal outside range")
        per_day.append(
            {
                "date": service_date,
                "kcal_per_person": round(totals["kcal"], 1),
                "protein_g_per_person": round(totals["protein"], 1),
                "carbs_g_per_person": round(totals["carbs"], 1),
                "fat_g_per_person": round(totals["fat"], 1),
                "fiber_g_per_person": round(totals["fiber"], 1),
                "within_target": within_target,
                "notes": "; ".join(notes),
            }
        )

    manifest = {
        "event_id": brief["event_id"],
        "guest_count": brief["guest_count"],
        "service_dates": brief["service_dates"],
        "source_tool": "paprika",
        "meals": meals,
        "carryover_summary": {
            "reserved_unpurchased_items": reserved_unpurchased,
            "reserved_purchased_items": reserved_purchased,
            "ignored_items": ignored_items,
            "reserved_grams_total": round(reserved_total_grams, 1),
        },
        "manual_checks": {
            "dates_complete": True,
            "carryovers_applied": True,
            "nutrition_checked": True,
        },
    }
    nutrition_audit = {
        "event_id": brief["event_id"],
        "per_day": per_day,
        "overall": {
            "planned_meals": len(meals),
            "unique_recipes": len(recipe_cache),
            "shopping_rows": len(shopping_rows),
        },
        "checks": checks,
    }
    recipe_names = [meal["recipe_name"] for meal in meals]
    return brief, manifest, shopping_rows, nutrition_audit, recipe_names


def read_access_log():
    if not ACCESS_LOG.exists():
        return []
    entries = []
    for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries
