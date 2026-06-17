# Fitness & Nutrition

Search for fitness and nutrition information using public data sources. Use this skill when the user needs exercise details, nutrition lookups, or body-composition calculations.

## Capabilities

- Search exercises from the public WGER exercise database.
- Search foods and nutrient values from USDA FoodData Central.
- Calculate BMI, TDEE, 1RM, body-fat estimate, and macro targets.

## Exercise Search

- Use WGER exercise data.
- Prefer approved exercises only.
- Prefer English exercise names when multiple languages exist.
- Filter by muscle group, equipment, category, or name as needed.

## Food Search

- Use USDA FoodData Central style nutrition data.
- Treat nutrient values as per-100g unless a record explicitly says otherwise.
- Scale calories and macros linearly from the source data to the requested gram amount.

## Calculations

- BMI
- TDEE using Mifflin-St Jeor
- 1RM using standard barbell estimation formulas
- Macro planning for cut, bulk, or maintenance

## References

- See `references/FORMULAS.md` for the formula details used by this skill copy.
- See `scripts/body_calc.py` for a reusable offline calculator implementation.
