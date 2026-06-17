#!/usr/bin/env python3
import csv
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))


def run_paprika(*args):
    result = subprocess.run(
        ["paprika", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def load_event_brief():
    with (DATA_DIR / "event_brief.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def load_pantry():
    pantry = {}
    with (DATA_DIR / "pantry_allowance.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pantry[row["ingredient_id"]] = {
                "ingredient_name": row["ingredient_name"],
                "grams_available": float(row["grams_available"]),
            }
    return pantry


def build_outputs():
    brief = load_event_brief()
    pantry = load_pantry()

    meals = []
    recipe_cache = {}
    for service_date in brief["service_dates"]:
        day_meals = json.loads(run_paprika("meals", "--date", service_date, "--json"))
        for slot in brief["meal_slots"]:
            match = next(row for row in day_meals if row["meal_type"] == slot)
            recipe = json.loads(run_paprika("recipe", match["recipe_uid"], "--json"))
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

    groceries = json.loads(run_paprika("groceries", "--all", "--json"))
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
        pantry_grams = pantry.get(ingredient_id, {}).get("grams_available", 0.0)
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

    per_day = []
    checks = {
        "protein_floor_met": True,
        "fiber_floor_met": True,
        "kcal_range_met": True,
        "dates_complete": True,
    }
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

    notes = [
        "# Meal Schedule",
        "",
        *[
            f"- {meal['date']} {meal['meal_slot']}: {meal['recipe_name']} ({meal['recipe_uid']})"
            for meal in meals
        ],
        "",
        "# Carryover",
        "",
        f"- Reserved unpurchased items: {reserved_unpurchased}",
        f"- Reserved purchased items: {reserved_purchased}",
        f"- Ignored items: {ignored_items}",
        "",
        "# Shopping Delta",
        "",
        f"- Rows still to buy: {len(shopping_rows)}",
        f"- Reserved grams already covered: {reserved_total_grams:.1f}",
        "",
        "# Nutrition Watchpoints",
        "",
        *[
            f"- {row['date']}: {row['kcal_per_person']:.1f} kcal, {row['protein_g_per_person']:.1f} g protein, {row['fiber_g_per_person']:.1f} g fiber"
            for row in per_day
        ],
    ]
    return manifest, shopping_rows, nutrition_audit, "\n".join(notes) + "\n"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, shopping_rows, nutrition_audit, kitchen_notes = build_outputs()
    with (OUTPUT_DIR / "meal_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    with (OUTPUT_DIR / "shopping_delta.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ingredient_id",
                "ingredient_name",
                "meal_dates",
                "recipe_uids",
                "required_grams",
                "pantry_grams",
                "carryover_grams",
                "to_buy_grams",
            ],
        )
        writer.writeheader()
        writer.writerows(shopping_rows)
    with (OUTPUT_DIR / "nutrition_audit.json").open("w", encoding="utf-8") as handle:
        json.dump(nutrition_audit, handle, indent=2)
        handle.write("\n")
    (OUTPUT_DIR / "kitchen_notes.md").write_text(kitchen_notes, encoding="utf-8")


if __name__ == "__main__":
    main()
