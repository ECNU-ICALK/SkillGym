from __future__ import annotations


ACTIVITY_FACTORS = {
    "sedentary": 1.20,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "athlete": 1.90,
}


def bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100.0
    return weight_kg / (height_m ** 2)


def bmr_mifflin(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if sex.lower() == "male":
        return base + 5
    return base - 161


def tdee(weight_kg: float, height_cm: float, age: int, sex: str, activity_level: str) -> float:
    return bmr_mifflin(weight_kg, height_cm, age, sex) * ACTIVITY_FACTORS[activity_level]


def epley_1rm(load_kg: float, reps: int) -> float:
    return load_kg * (1 + reps / 30.0)


def macro_targets(weight_kg: float, target_calories: float, protein_g_per_kg: float, fat_g_per_kg: float) -> dict:
    protein = weight_kg * protein_g_per_kg
    fat = weight_kg * fat_g_per_kg
    carbs = (target_calories - protein * 4 - fat * 9) / 4
    return {"protein_g": protein, "fat_g": fat, "carbs_g": carbs}
