# README – Factorio Assignment

## Overview

This submission includes two independent command-line tools: `factory/main.py` and `belts/main.py`. Both programs take structured JSON input via stdin and produce JSON output via stdout. They are written in Python 3.11 and run without additional dependencies beyond the standard scientific stack (OR-Tools for linear optimization).

---

## A. Factory Planner

### Purpose
Determines how to operate a set of machines and recipes so that a target item is produced at a fixed rate without exceeding machine or raw material limits.

### Main Approach
The system of recipes is converted into a linear optimization model:

- **Decision variables** represent how many crafts per minute each recipe runs.
- **Item balance equations** ensure every intermediate item is steady (no net loss or accumulation).
- **Raw items** may only be consumed up to given supply limits.
- **Machine usage** per type is restricted by its count limit.

The solver minimizes total machine usage while exactly meeting the target output rate. If the target cannot be achieved, the model relaxes the requirement and computes the maximum feasible rate.

### Highlights

- Uses OR-Tools LinearSolver (HiGHS) for stable LP solving.
- Productivity affects outputs only; speed affects craft rate.
- Deterministic behavior through sorted keys and fixed tolerances.
- Returns either an optimal machine plan or a clear infeasibility report with the limiting factors.

---

## B. Belt Network Flow

### Purpose
Models material transport between nodes with edge lower/upper limits and optional node throughput caps, similar to conveyor belts with minimum and maximum flow rates.

### Core Technique

1. **Node capacity splitting** — each capped node is replaced by an "in" and "out" node with a connecting edge whose capacity equals the node's limit.
2. **Lower-bound conversion** — every edge `[lo, hi]` becomes `[0, hi−lo]`, and the corresponding flow demand adjustments are recorded at its endpoints.
3. **Feasibility test** — a super-source/sink is added and Dinic's algorithm is run to see if all demand balances can be satisfied.

If feasible, the final flow on each edge is recovered and verified against all bounds and caps. If not, the algorithm reports which nodes or edges are responsible for the cut that prevents further flow.

### Key Features

- Deterministic Dinic implementation (sorted nodes and edges).
- Small numerical tolerance (`1e-9`) for all comparisons.
- Fast runtime on small and medium-sized graphs.

---

## C. Common Implementation Notes

- Both modules are single-threaded and deterministic.
- Inputs are validated and outputs are formatted consistently.
- The provided `gen_factory.py` and `gen_belts.py` scripts can generate random valid (and some infeasible) test cases.
- All scripts complete comfortably within 1–2 seconds on a standard laptop.

---

## D. Dependencies

- Python 3.11 or newer
- OR-Tools ≥ 9.9 (for `factory`)
- Standard library only for `belts`

---

## E. References Used

- Dinic's algorithm and lower-bound transformation – [CP-Algorithms](https://cp-algorithms.com/)
- Vertex capacity splitting – standard flow modeling technique