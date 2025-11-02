#!/usr/bin/env python3
"""
gen_factory.py
Generates *random but valid* factory problem instances for testing factory/main.py.

Usage:
  python gen_factory.py > input.json
  python gen_factory.py 5 > cases.json
  python gen_factory.py 1 42 > input.json   # 1 case, deterministic with seed 42
"""

import json
import random
import sys


def make_factory_case(seed: int = None):
    if seed is not None:
        random.seed(seed)

    # --- Machines ---
    machine_types = ["assembler_1", "assembler_2", "chemical", "furnace"]
    machines = {}
    for m in machine_types:
        machines[m] = {"crafts_per_min": round(random.uniform(10, 120), 3)}

    # --- Modules ---
    modules = {}
    for m in machine_types:
        if random.random() < 0.6:  # 60% chance to have modules
            modules[m] = {
                "prod": round(random.uniform(0.0, 0.25), 3),
                "speed": round(random.uniform(0.0, 0.25), 3),
            }
        else:
            modules[m] = {"prod": 0.0, "speed": 0.0}

    # --- Base resources ---
    raw_items = ["iron_ore", "copper_ore", "coal", "petroleum_gas", "water"]
    raw_supply = {
        r: round(random.uniform(5000, 500000), 2) for r in raw_items
    }

    # --- Recipes chain selection ---
    recipes = {}

    # Base smelting
    recipes["iron_plate"] = {
        "machine": "furnace",
        "time_s": 3.2,
        "in": {"iron_ore": 1},
        "out": {"iron_plate": 1},
    }
    recipes["copper_plate"] = {
        "machine": "furnace",
        "time_s": 3.2,
        "in": {"copper_ore": 1},
        "out": {"copper_plate": 1},
    }

    # Optional early branching
    if random.random() < 0.8:
        recipes["copper_cable"] = {
            "machine": random.choice(["assembler_1", "assembler_2"]),
            "time_s": 0.5,
            "in": {"copper_plate": 1},
            "out": {"copper_cable": 2},
        }

    # Green circuits
    recipes["green_circuit"] = {
        "machine": random.choice(["assembler_1", "assembler_2"]),
        "time_s": 0.5,
        "in": {"iron_plate": 1, "copper_cable": 3},
        "out": {"green_circuit": 1},
    }

    # Optionally red circuits chain
    if random.random() < 0.5:
        recipes["plastic_bar"] = {
            "machine": "chemical",
            "time_s": 1.0,
            "in": {"petroleum_gas": 20, "coal": 1},
            "out": {"plastic_bar": 2},
        }
        recipes["red_circuit"] = {
            "machine": random.choice(["assembler_1", "assembler_2"]),
            "time_s": 6.0,
            "in": {
                "green_circuit": 2,
                "copper_cable": 4,
                "plastic_bar": 2,
            },
            "out": {"red_circuit": 1},
        }

    # Optionally add a battery chain
    if random.random() < 0.4:
        recipes["sulfur"] = {
            "machine": "chemical",
            "time_s": 1.0,
            "in": {"petroleum_gas": 30, "water": 30},
            "out": {"sulfur": 2},
        }
        recipes["sulfuric_acid"] = {
            "machine": "chemical",
            "time_s": 1.0,
            "in": {"sulfur": 5, "iron_plate": 1, "water": 100},
            "out": {"sulfuric_acid": 50},
        }
        recipes["battery"] = {
            "machine": "chemical",
            "time_s": 4.0,
            "in": {
                "iron_plate": 1,
                "copper_plate": 1,
                "sulfuric_acid": 20,
            },
            "out": {"battery": 1},
        }

    # --- Limits ---
    max_machines = {
        m: random.randint(50, 500) for m in machine_types
    }

    # --- Target selection ---
    all_outputs = [list(r["out"].keys())[0] for r in recipes.values()]
    target_item = random.choice(all_outputs)
    target_rate = random.choice([120, 300, 600, 900, 1800])

    # --- Final payload ---
    data = {
        "machines": machines,
        "recipes": recipes,
        "modules": modules,
        "limits": {
            "raw_supply_per_min": raw_supply,
            "max_machines": max_machines,
        },
        "target": {"item": target_item, "rate_per_min": target_rate},
    }
    return data


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    cases = [make_factory_case(seed + i if seed else None) for i in range(n)]

    if n == 1:
        print(json.dumps(cases[0], indent=2))
    else:
        print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
