"""Helper script to generate BDEW normalised profile CSV files.

Run once: python data/bdew/generate_profiles.py
"""

import csv
import os

SEASONS = ["winter", "sommer", "uebergang"]
DAY_TYPES = ["werktag", "samstag", "sonntag"]

# Representative normalised BDEW profile shapes (96 slots per day, kW per 1000 kWh/a)
# Values are proportional fractions that integrate to 1000 kWh/a when summed × 0.25 h
# Real BDEW tables; these are simplified representative values per the spec.

# Each profile: dict keyed by (saison, tagesart) → list of 96 quarter-hour values
# Values in kW per 1000 kWh/a.  Sum of all slots across all day combos × weights = 1000/0.25.

# We generate synthetic but plausible profiles that sum to 1000 kWh/a.
# The normalised profile must satisfy: sum(all 35040 values) * 0.25 ≈ 1000 kWh

# Approximate day counts per season/daytype for a typical non-leap year:
# Winter ~141 days, Sommer ~123 days, Uebergang ~101 days
# Each season has ~Werktag 5/7, Samstag 1/7, Sonntag 1/7 of days

# We use simple daily load shapes per profile type
# All values in kW per 1000 kWh/a

def make_flat_shape(base, slots=96):
    """Flat load profile."""
    return [base] * slots


def make_residential_shape(season, daytype):
    """H0: household with morning and evening peaks."""
    base = [0.08] * 96
    # Morning peak 7-9h (slots 28-35)
    for i in range(28, 36):
        base[i] = 0.18
    # Lunch 12-13h (slots 48-51)
    for i in range(48, 52):
        base[i] = 0.14
    # Evening peak 17-21h (slots 68-83)
    for i in range(68, 84):
        base[i] = 0.22
    # Night reduction 23-5h (slots 92-96 + 0-19)
    for i in list(range(92, 96)) + list(range(0, 20)):
        base[i] = 0.04
    if season == "sommer":
        base = [v * 0.85 for v in base]
    elif season == "winter":
        base = [v * 1.15 for v in base]
    if daytype == "samstag":
        # Shift peak later
        for i in range(28, 36):
            base[i] = base[i] * 0.9
        for i in range(68, 84):
            base[i] = base[i] * 1.05
    elif daytype == "sonntag":
        base = [v * 0.9 for v in base]
        for i in range(68, 84):
            base[i] = base[i] * 1.1
    return base


def make_commercial_shape(profile_type, season, daytype):
    """G0-G6: commercial profiles."""
    # G0: general commercial (mix)
    if profile_type == "G0":
        base = [0.07] * 96
        for i in range(32, 72):  # 8h-18h
            base[i] = 0.17
        for i in list(range(0, 24)) + list(range(84, 96)):
            base[i] = 0.02
    elif profile_type == "G1":  # weekday offices
        base = [0.02] * 96
        for i in range(32, 72):
            base[i] = 0.22
    elif profile_type == "G2":  # evening businesses
        base = [0.02] * 96
        for i in range(60, 88):
            base[i] = 0.20
    elif profile_type == "G3":  # continuous
        base = [0.12] * 96
    elif profile_type == "G4":  # shops
        base = [0.02] * 96
        for i in range(36, 76):
            base[i] = 0.18
    elif profile_type == "G5":  # bakeries
        base = [0.02] * 96
        for i in range(16, 36):
            base[i] = 0.28
        for i in range(36, 52):
            base[i] = 0.14
    elif profile_type == "G6":  # weekend businesses
        base = [0.02] * 96
        if daytype in ("samstag", "sonntag"):
            for i in range(36, 76):
                base[i] = 0.20
    else:
        base = [0.12] * 96

    if season == "winter":
        base = [v * 1.1 for v in base]
    elif season == "sommer":
        base = [v * 0.9 for v in base]

    if daytype == "sonntag" and profile_type in ("G1", "G4"):
        base = [v * 0.1 for v in base]
    elif daytype == "samstag" and profile_type == "G1":
        base = [v * 0.3 for v in base]

    return base


def make_agriculture_shape(profile_type, season, daytype):
    """L0-L2: agriculture profiles."""
    if profile_type == "L0":
        base = [0.10] * 96
        for i in range(24, 80):
            base[i] = 0.14
    elif profile_type == "L1":
        base = [0.06] * 96
        for i in range(24, 80):
            base[i] = 0.16
        if season == "sommer":
            base = [v * 1.3 for v in base]
    elif profile_type == "L2":
        base = [0.08] * 96
        for i in range(16, 88):
            base[i] = 0.13
    else:
        base = [0.10] * 96

    if daytype == "sonntag":
        base = [v * 0.7 for v in base]

    return base


def get_profile_shape(profile_type, season, daytype):
    if profile_type == "H0":
        return make_residential_shape(season, daytype)
    elif profile_type.startswith("G"):
        return make_commercial_shape(profile_type, season, daytype)
    elif profile_type.startswith("L"):
        return make_agriculture_shape(profile_type, season, daytype)
    return [0.12] * 96


def normalize_to_1000kwha(profile_type):
    """Generate and normalise a full profile so sum*0.25 ≈ 1000 for a typical year."""
    # Approximate annual day distribution
    season_daytype_days = {
        ("winter", "werktag"): 101,
        ("winter", "samstag"): 20,
        ("winter", "sonntag"): 20,
        ("sommer", "werktag"): 88,
        ("sommer", "samstag"): 18,
        ("sommer", "sonntag"): 17,
        ("uebergang", "werktag"): 72,
        ("uebergang", "samstag"): 15,
        ("uebergang", "sonntag"): 14,
    }

    total_energy = 0.0
    shapes = {}
    for (season, daytype), n_days in season_daytype_days.items():
        shape = get_profile_shape(profile_type, season, daytype)
        shapes[(season, daytype)] = shape
        total_energy += sum(shape) * 0.25 * n_days

    # Scale factor so that total_energy == 1000
    scale = 1000.0 / total_energy if total_energy > 0 else 1.0

    normalised = {}
    for (season, daytype), shape in shapes.items():
        normalised[(season, daytype)] = [v * scale for v in shape]

    return normalised


PROFILES = ["H0", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "L0", "L1", "L2"]

output_dir = os.path.join(os.path.dirname(__file__))

for profile_type in PROFILES:
    normalised = normalize_to_1000kwha(profile_type)
    filepath = os.path.join(output_dir, f"{profile_type}.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["saison", "tagesart", "slot_index", "value_kw_per_1000kwha"])
        for (season, daytype), shape in normalised.items():
            for slot_index, value in enumerate(shape):
                writer.writerow([season, daytype, slot_index, round(value, 8)])
    print(f"Generated {filepath}")

print("Done.")
