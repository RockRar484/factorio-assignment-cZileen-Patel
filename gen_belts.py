#!/usr/bin/env python3
"""
gen_belts.py
Generates random but valid (or deliberately infeasible) test inputs for belts/main.py.

Usage:
  python gen_belts.py > input.json
  python gen_belts.py 5 > inputs.json
  python gen_belts.py 3 42 > deterministic_cases.json

Output JSON matches belts/main.py input schema:
{
  "nodes": [...],
  "edges": [{"from":..,"to":..,"lo":..,"hi":..}, ...],
  "sources": {...},
  "sink": "sink",
  "node_caps": {...}
}
"""

import json
import random
import sys


def make_belt_case(seed: int = None, infeasible: bool = False):
    if seed is not None:
        random.seed(seed)

    # ---------------- Nodes ----------------
    n_internal = random.randint(2, 4)
    internal_nodes = [chr(ord("a") + i) for i in range(n_internal)]
    nodes = ["s1"] + internal_nodes + ["sink"]

    # ---------------- Edges ----------------
    edges = []
    all_edges = []

    # Always start with source → first node
    first_node = internal_nodes[0]
    lo = random.randint(10, 60)
    hi = lo + random.randint(50, 200)
    edges.append({"from": "s1", "to": first_node, "lo": lo, "hi": hi})

    # Chain internal nodes (a→b→c→sink)
    for i in range(len(internal_nodes) - 1):
        u = internal_nodes[i]
        v = internal_nodes[i + 1]
        lo = random.randint(10, 60)
        hi = lo + random.randint(50, 200)
        edges.append({"from": u, "to": v, "lo": lo, "hi": hi})

    # Final connection to sink
    last_node = internal_nodes[-1]
    lo = random.randint(0, 30)
    hi = lo + random.randint(50, 150)
    if infeasible:
        # Make it infeasible: restrict last edge capacity too low
        hi = max(10, lo + random.randint(10, 30))
    edges.append({"from": last_node, "to": "sink", "lo": lo, "hi": hi})

    # Add a few optional cross-links
    if random.random() < 0.3 and len(internal_nodes) > 2:
        u = internal_nodes[0]
        v = internal_nodes[-1]
        lo = random.randint(0, 20)
        hi = lo + random.randint(20, 100)
        edges.append({"from": u, "to": v, "lo": lo, "hi": hi})

    # ---------------- Sources ----------------
    total_supply = random.randint(80, 200)
    sources = {"s1": total_supply}

    # ---------------- Node caps ----------------
    node_caps = {}
    for node in internal_nodes:
        if random.random() < 0.7:  # 70% chance to cap a node
            node_caps[node] = random.randint(60, 200)

    # ---------------- Sink ----------------
    sink = "sink"

    return {
        "nodes": nodes,
        "edges": edges,
        "sources": sources,
        "sink": sink,
        "node_caps": node_caps,
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None

    cases = []
    for i in range(n):
        # Alternate between feasible and infeasible for diversity
        infeasible = (i % 2 == 1)
        cases.append(make_belt_case(seed + i if seed else None, infeasible))

    if n == 1:
        print(json.dumps(cases[0], indent=2))
    else:
        print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
