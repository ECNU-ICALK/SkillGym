import csv

from common import EXPECTED_OUTPUT_FILES, OUTPUT_DIR, SHOPPING_COLUMNS, expected_outputs, read_csv, read_json


def test_output_inventory():
    actual = {path.name for path in OUTPUT_DIR.iterdir()}
    assert actual == EXPECTED_OUTPUT_FILES


def test_meal_manifest_matches_expected():
    _, expected_manifest, _, _, _ = expected_outputs()
    actual_manifest = read_json(OUTPUT_DIR / "meal_manifest.json")
    assert actual_manifest["event_id"] == expected_manifest["event_id"]
    assert actual_manifest["guest_count"] == expected_manifest["guest_count"]
    assert actual_manifest["service_dates"] == expected_manifest["service_dates"]
    assert str(actual_manifest["source_tool"]).lower() == "paprika"
    assert actual_manifest["carryover_summary"] == expected_manifest["carryover_summary"]
    assert actual_manifest["manual_checks"] == expected_manifest["manual_checks"]
    assert len(actual_manifest["meals"]) == len(expected_manifest["meals"])
    for actual_meal, expected_meal in zip(actual_manifest["meals"], expected_manifest["meals"]):
        assert actual_meal["date"] == expected_meal["date"]
        assert actual_meal["meal_slot"] == expected_meal["meal_slot"]
        assert actual_meal["recipe_uid"] == expected_meal["recipe_uid"]
        assert actual_meal["recipe_name"] == expected_meal["recipe_name"]
        assert actual_meal["category"] == expected_meal["category"]
        assert int(actual_meal["servings_planned"]) == int(expected_meal["servings_planned"])
        assert actual_meal["tags"] == expected_meal["tags"]
        assert int(actual_meal["total_time_min"]) == int(expected_meal["total_time_min"])
        assert isinstance(actual_meal["source_ref"], str) and actual_meal["source_ref"].strip()


def test_shopping_delta_matches_expected():
    _, _, expected_rows, _, _ = expected_outputs()
    actual_rows = read_csv(OUTPUT_DIR / "shopping_delta.csv")
    if actual_rows:
        assert list(actual_rows[0].keys()) == SHOPPING_COLUMNS
    else:
        assert expected_rows == []
    assert len(actual_rows) == len(expected_rows)
    for actual_row, expected_row in zip(actual_rows, expected_rows):
        assert actual_row["ingredient_id"] == expected_row["ingredient_id"]
        assert actual_row["ingredient_name"] == expected_row["ingredient_name"]
        assert actual_row["meal_dates"] == expected_row["meal_dates"]
        assert actual_row["recipe_uids"] == expected_row["recipe_uids"]
        for field in ["required_grams", "pantry_grams", "carryover_grams", "to_buy_grams"]:
            assert float(actual_row[field]) == float(expected_row[field])


def test_nutrition_audit_matches_expected():
    _, _, _, expected_audit, _ = expected_outputs()
    actual_audit = read_json(OUTPUT_DIR / "nutrition_audit.json")
    assert actual_audit["event_id"] == expected_audit["event_id"]
    assert actual_audit["overall"] == expected_audit["overall"]
    assert actual_audit["checks"] == expected_audit["checks"]
    assert len(actual_audit["per_day"]) == len(expected_audit["per_day"])
    for actual_row, expected_row in zip(actual_audit["per_day"], expected_audit["per_day"]):
        assert actual_row["date"] == expected_row["date"]
        for field in [
            "kcal_per_person",
            "protein_g_per_person",
            "carbs_g_per_person",
            "fat_g_per_person",
            "fiber_g_per_person",
        ]:
            assert float(actual_row[field]) == float(expected_row[field])
        assert bool(actual_row["within_target"]) == bool(expected_row["within_target"])
        assert isinstance(actual_row["notes"], str)


def test_kitchen_notes_contract():
    _, expected_manifest, _, expected_audit, recipe_names = expected_outputs()
    content = (OUTPUT_DIR / "kitchen_notes.md").read_text(encoding="utf-8")
    lines = content.splitlines()
    assert lines[0] == "# Meal Schedule"
    assert "# Carryover" in content
    assert "# Shopping Delta" in content
    assert "# Nutrition Watchpoints" in content
    assert content.index("# Meal Schedule") < content.index("# Carryover") < content.index("# Shopping Delta") < content.index("# Nutrition Watchpoints")
    for recipe_name in recipe_names:
        assert recipe_name in content
    summary = expected_manifest["carryover_summary"]
    assert str(summary["reserved_unpurchased_items"]) in content
    assert str(summary["reserved_purchased_items"]) in content
    assert str(summary["ignored_items"]) in content
    assert str(expected_audit["overall"]["shopping_rows"]) in content
    for row in expected_audit["per_day"]:
        assert row["date"] in content
