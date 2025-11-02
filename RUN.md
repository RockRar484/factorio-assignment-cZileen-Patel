# RUN.md

##  Expected Environment

- **Python**: 3.11 or newer
- **Dependencies**:
  - `ortools` (for `factory/main.py`) — **Install with**: `pip install ortools`
  - No external libraries for `belts/main.py`
- Works on Windows, macOS, or Linux.

---


##  Running Sample Tests

Use the provided script to verify both modules on predefined sample cases.
```bash
python run_samples.py "python factory/main.py" "python belts/main.py"
```

This command:

- Runs all Factory test payloads on `factory/main.py`
- Runs all Belts test payloads on `belts/main.py`
- Prints formatted JSON outputs for each case to the terminal

You should see section headers such as:
```
# Running factory samples
## factory_modules_on_greens_1800
{ ... }

# Running belts samples
## belts_feasible_lower_bounds_node_cap
{ ... }
```

---

##  Running with Randomly Generated Tests

You can create your own test inputs using the generator scripts:

### Factory generator
```bash
python gen_factory.py > sample_factory.json
python factory/main.py < sample_factory.json
```

### Belts generator
```bash
python gen_belts.py > sample_belts.json
python belts/main.py < sample_belts.json
```

Each generator can produce multiple or seeded random cases, for example:
```bash
python gen_factory.py 5 > factories.json
python gen_belts.py 3 42 > belts.json
```

---

##  Automated Testing with Pytest

If you've included pytest test files (optional), you can define the solver commands as environment variables:
```bash
FACTORY_CMD="python factory/main.py" BELTS_CMD="python belts/main.py" pytest -q
```

This setup allows `pytest` tests to invoke the two CLI tools programmatically using the same command-line interface.

---


##  Output Format

Both programs output a single JSON object per run, with either:

- `"status": "optimal"` — if a valid plan or flow was found, or
- `"status": "infeasible"` — if constraints cannot be met.

All numeric results are rounded consistently for clarity and determinism.
