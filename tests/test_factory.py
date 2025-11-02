import subprocess, json, sys, os, tempfile

FACTORY_CMD = "python factory/main.py"

def run_case(json_obj):
    p = subprocess.Popen(FACTORY_CMD.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out, _ = p.communicate(json.dumps(json_obj).encode())
    return json.loads(out)

def test_simple_green():
    input_data = {
      "machines": {
        "assembler_1": {"crafts_per_min": 30},
        "chemical": {"crafts_per_min": 60}
      },
      "recipes": {
        "iron_plate": {"machine": "chemical", "time_s": 3.2, "in": {"iron_ore":1}, "out": {"iron_plate":1}},
        "copper_plate": {"machine": "chemical", "time_s": 3.2, "in": {"copper_ore":1}, "out":{"copper_plate":1}},
        "green_circuit": {"machine":"assembler_1", "time_s": 0.5, "in":{"iron_plate":1,"copper_plate":3}, "out":{"green_circuit":1}}
      },
      "modules": {},
      "limits": {"raw_supply_per_min": {"iron_ore":5000,"copper_ore":5000}, "max_machines":{"assembler_1":300,"chemical":300}},
      "target": {"item":"green_circuit","rate_per_min":1800}
    }
    out = run_case(input_data)
    assert out["status"] in ("ok","infeasible")
