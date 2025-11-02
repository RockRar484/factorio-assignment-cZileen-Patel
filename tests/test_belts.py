# tests/test_belts.py
import json
import subprocess
import sys
from pathlib import Path

BELTS_CMD = "python belts/main.py"

def run_case(payload):
    p = subprocess.run(
        BELTS_CMD.split(),
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    out = p.stdout.decode("utf-8").strip()
    err = p.stderr.decode("utf-8")
    if out == "":
        # help debug if the script printed to stderr or crashed
        raise RuntimeError(f"No stdout from belts command. Stderr:\n{err}")
    try:
        return json.loads(out)
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON output. stdout:\n{out}\nstderr:\n{err}") from e

def test_belts_feasible_lower_bounds_node_cap():
    payload = {
        "nodes": ["s1", "a", "b", "sink"],
        "edges": [
            {"from": "s1", "to": "a", "lo": 50, "hi": 200},
            {"from": "a", "to": "b", "lo": 40, "hi": 150},
            {"from": "b", "to": "sink", "lo": 0, "hi": 120}
        ],
        "sources": {"s1": 120},
        "sink": "sink",
        # belts/main.py expects node_caps as simple numeric mapping (throughput value).
        "node_caps": {"b": 120}
    }
    out = run_case(payload)
    assert "status" in out
    assert out["status"] == "ok", f"Expected feasible case to be ok, got: {out}"

def test_belts_infeasible_cut():
    payload = {
        "nodes": ["s1", "a", "b", "sink"],
        "edges": [
            {"from": "s1", "to": "a", "lo": 50, "hi": 200},
            {"from": "a", "to": "b", "lo": 40, "hi": 150},
            {"from": "b", "to": "sink", "lo": 0, "hi": 60}
        ],
        "sources": {"s1": 120},
        "sink": "sink",
        "node_caps": {"b": 120}
    }
    out = run_case(payload)
    assert "status" in out
    assert out["status"] == "infeasible", f"Expected infeasible case, got: {out}"
