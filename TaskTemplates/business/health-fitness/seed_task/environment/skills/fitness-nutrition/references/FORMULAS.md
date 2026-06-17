# Fitness Nutrition Formulas

This local skill copy follows the public `fitness-nutrition` workflow described on SkillsMP.

## Body Metrics

- `BMI = weight_kg / (height_m ^ 2)`
- `BMR (Mifflin-St Jeor, male) = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5`
- `BMR (Mifflin-St Jeor, female) = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161`

## Activity Factors

- `sedentary = 1.20`
- `lightly_active = 1.375`
- `moderately_active = 1.55`
- `very_active = 1.725`
- `athlete = 1.90`

## Energy Target

- `TDEE = BMR * activity_factor`
- `cut target calories = TDEE - calorie_deficit_kcal`

## Strength Estimate

- Default 1RM formula for this task: `Epley = weight * (1 + reps / 30)`

## Macro Targets For Cut

- `protein_g = weight_kg * protein_g_per_kg`
- `fat_g = weight_kg * fat_g_per_kg`
- `carbs_g = (target_calories - protein_g * 4 - fat_g * 9) / 4`

## Rounding

- `BMI` to 2 decimals
- calorie and macro targets to 1 decimal
- training loads to the nearest configured `load_increment_kg`
- meal grams to the configured meal gram increment
