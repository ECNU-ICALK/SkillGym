#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(os.environ.get("PAPRIKA_DATA_DIR", "/opt/paprika_store"))
LOG_PATH = Path(os.environ.get("PAPRIKA_ACCESS_LOG", "/var/log/paprika_access.log"))


def load_json(name):
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


RECIPES = load_json("recipes.json")
MEALS = load_json("meals.json")
GROCERIES = load_json("groceries.json")
RECIPES_BY_UID = {row["uid"]: row for row in RECIPES}


def recipe_summary(row):
    return {
        "uid": row["uid"],
        "name": row["name"],
        "category": row["category"],
        "servings": row["servings"],
        "tags": row["tags"],
        "total_time_min": row["total_time_min"],
    }


def log_call(argv):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "argv": argv,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def print_json(data):
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


def find_recipe(query):
    if query in RECIPES_BY_UID:
        return RECIPES_BY_UID[query]
    lowered = query.lower()
    exact = [row for row in RECIPES if row["name"].lower() == lowered]
    if exact:
        return exact[0]
    partial = [row for row in RECIPES if lowered in row["name"].lower()]
    if len(partial) == 1:
        return partial[0]
    if partial:
        names = ", ".join(row["name"] for row in partial)
        raise SystemExit(f"Multiple recipes matched: {names}")
    raise SystemExit(f"No recipe matched: {query}")


def command_recipes(args):
    category = None
    as_json = False
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--category":
            index += 1
            if index >= len(args):
                raise SystemExit("Missing value after --category")
            category = args[index]
        elif token == "--json":
            as_json = True
        else:
            raise SystemExit(f"Unknown flag for recipes: {token}")
        index += 1
    rows = RECIPES
    if category is not None:
        rows = [row for row in rows if row["category"].lower() == category.lower()]
    if as_json:
        print_json([recipe_summary(row) for row in rows])
        return
    for row in rows:
        print(f"{row['uid']}\t{row['category']}\t{row['name']}")


def command_recipe(args):
    if not args:
        raise SystemExit("Usage: paprika recipe <uid-or-name> [--json] [--ingredients-only]")
    query = args[0]
    flags = args[1:]
    as_json = "--json" in flags
    ingredients_only = "--ingredients-only" in flags
    for token in flags:
        if token not in {"--json", "--ingredients-only"}:
            raise SystemExit(f"Unknown flag for recipe: {token}")
    recipe = find_recipe(query)
    if as_json:
        print_json(recipe)
        return
    if ingredients_only:
        for item in recipe["ingredients"]:
            print(f"{item['ingredient_name']}\t{item['grams']}g")
        return
    print(f"{recipe['uid']}: {recipe['name']}")
    print(f"Category: {recipe['category']}")
    print(f"Servings: {recipe['servings']}")
    print(f"Total time: {recipe['total_time_min']} min")
    for item in recipe["ingredients"]:
        print(f"- {item['ingredient_name']}: {item['grams']}g")


def command_search(args):
    if not args:
        raise SystemExit("Usage: paprika search <term>")
    term = " ".join(args).lower()
    rows = [
        row for row in RECIPES
        if term in row["name"].lower()
        or any(term in tag.lower() for tag in row["tags"])
    ]
    for row in rows:
        print(f"{row['uid']}\t{row['name']}")


def command_meals(args):
    date = None
    as_json = False
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--date":
            index += 1
            if index >= len(args):
                raise SystemExit("Missing value after --date")
            date = args[index]
        elif token == "--json":
            as_json = True
        else:
            raise SystemExit(f"Unknown flag for meals: {token}")
        index += 1
    rows = MEALS
    if date is not None:
        rows = [row for row in rows if row["date"] == date]
    enriched = []
    for row in rows:
        recipe = RECIPES_BY_UID[row["recipe_uid"]]
        enriched.append(
            {
                "date": row["date"],
                "meal_type": row["meal_type"],
                "recipe_uid": recipe["uid"],
                "recipe_name": recipe["name"],
                "category": recipe["category"],
            }
        )
    if as_json:
        print_json(enriched)
        return
    for row in enriched:
        print(f"{row['date']}\t{row['meal_type']}\t{row['recipe_uid']}\t{row['recipe_name']}")


def command_groceries(args):
    include_purchased = False
    as_json = False
    for token in args:
        if token == "--all":
            include_purchased = True
        elif token == "--json":
            as_json = True
        else:
            raise SystemExit(f"Unknown flag for groceries: {token}")
    rows = GROCERIES if include_purchased else [row for row in GROCERIES if not row["purchased"]]
    if as_json:
        print_json(rows)
        return
    for row in rows:
        state = "purchased" if row["purchased"] else "open"
        print(
            f"{row['item_id']}\t{row['ingredient_id']}\t{row['ingredient_name']}\t"
            f"{row['grams']}g\t{state}\t{row['reserved_event_id']}"
        )


def command_categories(args):
    if args:
        raise SystemExit("Usage: paprika categories")
    for category in sorted({row["category"] for row in RECIPES}):
        print(category)


def command_auth(args):
    if args:
        raise SystemExit("Usage: paprika auth")
    print("Paprika auth is already satisfied in this workspace.")


def main(argv):
    log_call(argv)
    if len(argv) < 2:
        print("Paprika CLI ready. Commands: recipes, recipe, search, meals, groceries, categories, auth")
        return 0
    command = argv[1]
    args = argv[2:]
    if command == "recipes":
        command_recipes(args)
    elif command == "recipe":
        command_recipe(args)
    elif command == "search":
        command_search(args)
    elif command == "meals":
        command_meals(args)
    elif command == "groceries":
        command_groceries(args)
    elif command == "categories":
        command_categories(args)
    elif command == "auth":
        command_auth(args)
    else:
        raise SystemExit(f"Unknown command: {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
