#!/usr/bin/env python3
# factory/main.py
"""
Reads JSON from stdin, writes JSON to stdout.
Uses OR-Tools pywraplp to solve the steady-state LP and minimize machine count.
"""
import sys
import json
from math import isclose
from ortools.linear_solver import pywraplp

TOL = 1e-9

def read_input():
    return json.load(sys.stdin)

def write_output(obj):
    json.dump(obj, sys.stdout, separators=(",", ":"))

def build_and_solve(data, maximize_target=False):
    machines = data.get("machines", {})
    recipes = data.get("recipes", {})
    modules = data.get("modules", {})
    limits = data.get("limits", {})
    raw_caps = limits.get("raw_supply_per_min", {})
    max_machines = limits.get("max_machines", {})
    target = data.get("target", {})
    target_item = target.get("item")
    requested_rate = float(target.get("rate_per_min", 0.0))

    # Precompute recipe -> machine, eff crafts/min and productivity multiplier
    eff = {}
    prod = {}
    for rname, r in recipes.items():
        mname = r["machine"]
        machine_def = machines.get(mname, {})
        base_cpm = float(machine_def.get("crafts_per_min"))
        mod = modules.get(mname, {})
        speed = float(mod.get("speed", 0.0))
        prod_m = float(mod.get("prod", 0.0))
        time_s = float(r["time_s"])
        eff_r = base_cpm * (1.0 + speed)
        eff[rname] = eff_r
        prod[rname] = prod_m

    solver = pywraplp.Solver.CreateSolver("GLOP")  # continuous LP
    if solver is None:
        # fallback to CBC if GLOP not available
        solver = pywraplp.Solver.CreateSolver("CBC")

    # Variables: x_r >= 0 (crafts/min)
    x = {}
    for rname in recipes:
        x[rname] = solver.NumVar(0.0, solver.infinity(), f"x[{rname}]")

    # For raw items, we introduce consumption variable c_i >= 0 and <= cap
    items = set()
    # print()
    for r in recipes.values():
        items.update(r.get("in", {}).keys())
        items.update(r.get("out", {}).keys())
    items = sorted(items)

    # Build item constraints: sum_out * (1+prod_r_of_machine) * x_r - sum_in * x_r + consumption_raw = b[i]
    # For intermediates: RHS = 0
    # For target: RHS = target_rate (or variable if maximizing target)
    # For raw items: RHS = 0 and consumption_raw variable is present constrained 0..cap (and moves to LHS)
    consumption = {}
    item_constraints = {}
    for it in items:
        # Left side expression coefficients prepared via constraints
        # We'll create a constraint equal to RHS later.
        # But OR-Tools requires building constraints directly.
        pass

    # Create consumption variables and constraints per item
    for it in items:
        # Build linear expression coefficients for x variables
        coeffs = []
        for rname, r in recipes.items():
            out = r.get("out", {})
            inn = r.get("in", {})
            out_qty = float(out.get(it, 0))
            in_qty = float(inn.get(it, 0))
            # Output scaled by productivity of that recipe's machine
            mult = 1.0 + prod[rname]
            # contribution = out_qty * mult * x_r - in_qty * x_r
            coeff = out_qty * mult - in_qty
            if abs(coeff) > 0:
                coeffs.append((x[rname], coeff))

        # RHS determination
        is_target = (it == target_item)
        is_raw = (it in raw_caps)

        if is_raw:
            # create consumption var
            cap = float(raw_caps[it])
            c = solver.NumVar(0.0, cap, f"consumption[{it}]")
            consumption[it] = c
            # constraint: sum_coeffs + c = (target? unlikely for raw)  => RHS 0 normally
            if is_target:
                rhs = float(requested_rate) if not maximize_target else solver.NumVar(0.0, solver.infinity(), "target_var")
            else:
                rhs = 0.0
            cons = solver.Constraint(rhs, rhs)
            # add coefficients
            for var, coeff in coeffs:
                cons.SetCoefficient(var, coeff)
            cons.SetCoefficient(c, 1.0)  # + c
            item_constraints[it] = cons
        else:
            # intermediate or target (non-raw)
            if is_target:
                if maximize_target:
                    # create a variable for target rate to maximize
                    target_var = solver.NumVar(0.0, solver.infinity(), "target_var")
                    rhs_var = target_var
                else:
                    rhs_var = float(requested_rate)
            else:
                rhs_var = 0.0
            # create equality constraint
            if isinstance(rhs_var, float):
                cons = solver.Constraint(rhs_var, rhs_var)
            else:
                cons = solver.Constraint(0.0, 0.0)  # we'll handle by moving var to LHS
            # set coefficients
            for var, coeff in coeffs:
                cons.SetCoefficient(var, coeff)
            if not isinstance(rhs_var, float):
                # move target_var to LHS as -1 * target_var
                cons.SetCoefficient(rhs_var, -1.0)
            item_constraints[it] = cons

    # Machine usage constraints
    machine_usage_cons = {}
    for mname in machines:
        cons = solver.Constraint(0.0, float(max_machines.get(mname, float("inf"))))
        # sum_r x_r / eff_r <= max_machines[m]
        for rname, r in recipes.items():
            if r["machine"] == mname:
                if eff[rname] <= 0:
                    # un-runnable recipe -> force x_r == 0
                    solver.Add(x[rname] == 0.0)
                else:
                    cons.SetCoefficient(x[rname], 1.0 / eff[rname])
        machine_usage_cons[mname] = cons

    # Objective: minimize total machines (sum_r x_r / eff_r)
    objective = solver.Objective()
    for rname in recipes:
        if eff[rname] > 0:
            objective.SetCoefficient(x[rname], 1.0 / eff[rname])
    if maximize_target:
        # If maximizing target, objective will be set later
        pass
    else:
        objective.SetMinimization()

    # If infeasible detection mode: we will allow target_var and maximize it
    if maximize_target:
        # Rebuild solver in maximize mode: we already created target_var earlier if needed
        # Simpler approach: create a new solver formulation specifically for maximizing target
        pass

    # Solve feasibility/minimization
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        # collect outputs
        per_recipe = {r: float(x[r].solution_value()) for r in recipes}
        per_machine_counts = {}
        for mname in machines:
            usage = 0.0
            for rname, r in recipes.items():
                if r["machine"] == mname:
                    if eff[rname] > 0:
                        usage += per_recipe[rname] / eff[rname]
            import math
            per_machine_counts[mname] = math.ceil(usage)
        raw_consumption = {}
        for it, cvar in consumption.items():
            raw_consumption[it] = float(cvar.solution_value())
        return {"status": "ok",
                "per_recipe_crafts_per_min": per_recipe,
                "per_machine_counts": per_machine_counts,
                "raw_consumption_per_min": raw_consumption}
    else:
        # infeasible: compute maximal feasible target rate via a separate LP
        # Build a maximizing solver: maximize target_rate (a variable), subject to same constraints
        solver2 = pywraplp.Solver.CreateSolver("GLOP")
        if solver2 is None:
            solver2 = pywraplp.Solver.CreateSolver("CBC")
        # Recreate variables in solver2
        x2 = {}
        for rname in recipes:
            x2[rname] = solver2.NumVar(0.0, solver2.infinity(), f"x[{rname}]")
        # consumption2
        consumption2 = {}
        item_cons2 = {}
        target_var = solver2.NumVar(0.0, solver2.infinity(), "target_var")
        for it in items:
            coeffs = []
            for rname, r in recipes.items():
                out_qty = float(r.get("out", {}).get(it, 0))
                in_qty = float(r.get("in", {}).get(it, 0))
                coeff = out_qty * (1.0 + prod[rname]) - in_qty
                if abs(coeff) > 0:
                    coeffs.append((x2[rname], coeff))
            is_target = (it == target_item)
            is_raw = (it in raw_caps)
            if is_raw:
                cap = float(raw_caps[it])
                c = solver2.NumVar(0.0, cap, f"consumption[{it}]")
                consumption2[it] = c
                rhs = 0.0
                cons = solver2.Constraint(rhs, rhs)
                for var, coeff in coeffs:
                    cons.SetCoefficient(var, coeff)
                cons.SetCoefficient(c, 1.0)
                item_cons2[it] = cons
            else:
                if is_target:
                    cons = solver2.Constraint(0.0, 0.0)
                    for var, coeff in coeffs:
                        cons.SetCoefficient(var, coeff)
                    cons.SetCoefficient(target_var, -1.0)
                else:
                    cons = solver2.Constraint(0.0, 0.0)
                    for var, coeff in coeffs:
                        cons.SetCoefficient(var, coeff)
                item_cons2[it] = cons
        # machine constraints
        for mname in machines:
            cons = solver2.Constraint(0.0, float(max_machines.get(mname, float("inf"))))
            for rname, r in recipes.items():
                if r["machine"] == mname:
                    if eff[rname] <= 0:
                        solver2.Add(x2[rname] == 0.0)
                    else:
                        cons.SetCoefficient(x2[rname], 1.0 / eff[rname])
        # objective: maximize target_var
        obj = solver2.Objective()
        obj.SetCoefficient(target_var, 1.0)
        obj.SetMaximization()

        stat2 = solver2.Solve()
        if stat2 == pywraplp.Solver.OPTIMAL or stat2 == pywraplp.Solver.FEASIBLE:
            max_target = float(target_var.solution_value())
            # collect bottleneck hints: which machines/raws are at cap
            per_recipe = {r: float(x2[r].solution_value()) for r in recipes}
            per_machine_counts = {}
            tight = []
            for mname in machines:
                usage = 0.0
                for rname, r in recipes.items():
                    if r["machine"] == mname:
                        if eff[rname] > 0:
                            usage += per_recipe[rname] / eff[rname]
                per_machine_counts[mname] = usage
                if mname in max_machines:
                    if usage >= float(max_machines[mname]) - 1e-6:
                        tight.append(mname + " cap")
            raw_tight = []
            raw_consumption = {}
            for it, cvar in consumption2.items():
                val = float(cvar.solution_value())
                raw_consumption[it] = val
                if it in raw_caps and val >= float(raw_caps[it]) - 1e-6:
                    raw_tight.append(it + " supply")
            bottlenecks = tight + raw_tight
            return {"status": "infeasible",
                    "max_feasible_target_per_min": max_target,
                    "bottleneck_hint": bottlenecks}
        else:
            # totally impossible or numerical failure
            return {"status": "infeasible",
                    "max_feasible_target_per_min": 0.0,
                    "bottleneck_hint": ["unsatisfiable"]}

def main():
    data = read_input()
    out = build_and_solve(data, maximize_target=False)
    write_output(out)

if __name__ == "__main__":
    main()
