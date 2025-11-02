# run_samples.py
import json
import sys
import subprocess
from typing import Dict, Any, Tuple, List

TOL = 0.11

def run(cmd: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    p = subprocess.run(
        cmd.split(),
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    out = p.stdout.decode("utf-8").strip()
    err = p.stderr.decode("utf-8")
    try:
        return json.loads(out), out, err
    except Exception:
        print("STDOUT:")
        print(out)
        print("STDERR:")
        print(err)
        raise

# ---------------- Factory samples ----------------

FACTORY_SAMPLES: List[Dict[str, Any]] = [
    # 1) Modules ON — green circuits target 1,800/min
    {
        "name": "factory_modules_on_greens_1800",
        "payload": {
          "machines": {
            "assembler_1": {"crafts_per_min": 30},
            "chemical": {"crafts_per_min": 60}
          },
          "recipes": {
            "iron_plate": {"machine": "chemical","time_s": 3.2,"in": {"iron_ore": 1},"out": {"iron_plate": 1}},
            "copper_plate": {"machine": "chemical","time_s": 3.2,"in": {"copper_ore": 1},"out": {"copper_plate": 1}},
            "green_circuit": {"machine": "assembler_1","time_s": 0.5,"in": {"iron_plate": 1, "copper_plate": 3},"out": {"green_circuit": 1}}
          },
          "modules": {
            "assembler_1": {"prod": 0.1, "speed": 0.15},
            "chemical": {"prod": 0.2, "speed": 0.1}
          },
          "limits": {
            "raw_supply_per_min": {"iron_ore": 5000, "copper_ore": 5000},
            "max_machines": {"assembler_1": 300, "chemical": 300}
          },
          "target": {"item": "green_circuit", "rate_per_min": 1800}
        }
    },
    # 2) No modules — 120 green/min
    {
        "name": "factory_no_modules_greens_120",
        "payload": {
          "machines": {
            "assembler_1": {"crafts_per_min": 120},
            "assembler_2": {"crafts_per_min": 120},
            "chemical": {"crafts_per_min": 18.75}
          },
          "recipes": {
            "iron_plate": {"machine": "chemical","time_s": 3.2,"in": {"iron_ore": 1},"out": {"iron_plate": 1}},
            "copper_plate": {"machine": "chemical","time_s": 3.2,"in": {"copper_ore": 1},"out": {"copper_plate": 1}},
            "green_circuit": {"machine": "assembler_1","time_s": 0.5,"in": {"iron_plate": 1, "copper_cable": 3},"out": {"green_circuit": 1}},
            "copper_cable":{"machine": "assembler_2","time_s": 0.5,"in": {"copper_plate": 1},"out": {"copper_cable": 1}}
          },
          "modules": {
            "assembler_1": {"prod": 0, "speed": 0},
            "assembler_2": {"prod": 0, "speed": 0},
            "chemical": {"prod": 0, "speed": 0}
          },
          "limits": {
            "raw_supply_per_min": {"iron_ore": 5000, "copper_ore": 5000},
            "max_machines": {"assembler_1": 300, "assembler_2":300, "chemical": 300}
          },
          "target": {"item": "green_circuit", "rate_per_min": 120}
        }
    },
    # 3) Red circuits chain with modules — 600 red/min
    {
        "name": "factory_reds_full_chain_600",
        "payload": {
          "machines": {
            "stone_furnace": {"crafts_per_min": 1},
            "assembling_machine_2": {"crafts_per_min": 1},
            "chemical_plant": {"crafts_per_min": 1}
          },
          "recipes": {
            "plastic": {"machine": "chemical_plant","time_s": 1.0,"in": {"petroleum_gas": 20, "coal": 1},"out": {"plastic_bar": 2}},
            "copper_cable": {"machine": "assembling_machine_2","time_s": 0.5,"in": {"copper_plate": 1},"out": {"copper_cable": 2}},
            "green_circuit": {"machine": "assembling_machine_2","time_s": 0.5,"in": {"iron_plate": 1, "copper_cable": 3},"out": {"green_circuit": 1}},
            "red_circuit": {"machine": "assembling_machine_2","time_s": 6.0,"in": {"green_circuit": 2, "copper_cable": 4, "plastic_bar": 2},"out": {"red_circuit": 1}},
            "iron_plate": {"machine": "stone_furnace","time_s": 3.2,"in": {"iron_ore": 1},"out": {"iron_plate": 1}},
            "copper_plate": {"machine": "stone_furnace","time_s": 3.2,"in": {"copper_ore": 1},"out": {"copper_plate": 1}}
          },
          "modules": {
            "assembling_machine_2": {"speed": 0.25, "prod": 0.2},
            "chemical_plant": {"speed": 0.2, "prod": 0.15},
            "stone_furnace": {"speed": 0.1}
          },
          "limits": {
            "raw_supply_per_min": {
              "iron_ore": 100000,
              "copper_ore": 100000,
              "petroleum_gas": 1000000,
              "coal": 100000
            },
            "max_machines": {
              "assembling_machine_2": 100000,
              "chemical_plant": 100000,
              "stone_furnace": 100000
            }
          },
          "target": {"item": "red_circuit", "rate_per_min": 600}
        }
    },
    # 4) Batteries chain with modules — 300 battery/min
    {
        "name": "factory_batteries_chain_300",
        "payload": {
          "machines": {
            "stone_furnace": {"crafts_per_min": 1},
            "chemical_plant": {"crafts_per_min": 1}
          },
          "recipes": {
            "sulfur": {"machine": "chemical_plant","time_s": 1.0,"in": {"petroleum_gas": 30, "water": 30},"out": {"sulfur": 2}},
            "sulfuric_acid": {"machine": "chemical_plant","time_s": 1.0,"in": {"sulfur": 5, "iron_plate": 1, "water": 100},"out": {"sulfuric_acid": 50}},
            "battery": {"machine": "chemical_plant","time_s": 4.0,"in": {"iron_plate": 1, "copper_plate": 1, "sulfuric_acid": 20},"out": {"battery": 1}},
            "iron_plate": {"machine": "stone_furnace","time_s": 3.2,"in": {"iron_ore": 1},"out": {"iron_plate": 1}},
            "copper_plate": {"machine": "stone_furnace","time_s": 3.2,"in": {"copper_ore": 1},"out": {"copper_plate": 1}}
          },
          "modules": {
            "chemical_plant": {"speed": 0.2, "prod": 0.15},
            "stone_furnace": {"speed": 0.1}
          },
          "limits": {
            "raw_supply_per_min": {
              "iron_ore": 100000,
              "copper_ore": 100000,
              "petroleum_gas": 1000000,
              "water": 1000000
            },
            "max_machines": {
              "chemical_plant": 100000,
              "stone_furnace": 100000
            }
          },
          "target": {"item": "battery", "rate_per_min": 300}
        }
    },
]

# ---------------- Belts samples ----------------

BELTS_SAMPLES: List[Dict[str, Any]] = [
    # 1) Feasible with lower bounds and one node cap
    {
        "name": "belts_feasible_lower_bounds_node_cap",
        "payload": {
            "nodes": ["s1","a","b","sink"],
            "edges": [
                {"from":"s1","to":"a","lo":50,"hi":200},
                {"from":"a","to":"b","lo":40,"hi":150},
                {"from":"b","to":"sink","lo":0,"hi":120}
            ],
            "sources": {"s1": 120},
            "sink": "sink",
            # normalize to numeric throughput (belts/main.py expects number)
            "node_caps": {"b": 120}
        }
    },
    # 2) Infeasible: cut tight on b->sink capacity
    {
        "name": "belts_infeasible_cut",
        "payload": {
            "nodes": ["s1","a","b","sink"],
            "edges": [
                {"from":"s1","to":"a","lo":50,"hi":200},
                {"from":"a","to":"b","lo":40,"hi":150},
                {"from":"b","to":"sink","lo":0,"hi":60}  # too small
            ],
            "sources": {"s1": 120},
            "sink": "sink",
            "node_caps": {"b": 120}
        }
    }
]

def pretty_print(name: str, obj: Dict[str, Any]):
    print("##", name)
    print(json.dumps(obj, indent=2, ensure_ascii=False, separators=(",", ":")))
    print()

def main():
    if len(sys.argv) < 3:
        print('Usage: python run_samples.py "python factory/main.py" "python belts/main.py"')
        sys.exit(2)

    factory_cmd = sys.argv[1]
    belts_cmd = sys.argv[2]

    print("# Running factory samples\n")
    for case in FACTORY_SAMPLES:
        try:
            got, raw_out, raw_err = run(factory_cmd, case["payload"])
        except Exception as e:
            print(f"## {case['name']} - error running sample")
            print(str(e))
            continue
        pretty_print(case["name"], got)

    print("# Running belts samples\n")
    for case in BELTS_SAMPLES:
        try:
            got, raw_out, raw_err = run(belts_cmd, case["payload"])
        except Exception as e:
            print(f"## {case['name']} - error running sample")
            print(str(e))
            continue
        pretty_print(case["name"], got)

if __name__ == "__main__":
    main()
