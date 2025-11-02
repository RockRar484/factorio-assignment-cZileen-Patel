#!/usr/bin/env python3
# belts/main.py
# Reads JSON from stdin, writes JSON to stdout.
# Implements Dinic and lower-bound + node-capacity reduction.

import sys
import json
from collections import deque, defaultdict

EPS = 1e-9
INF = 10**18

class Dinic:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]

    def add_edge(self, u, v, cap):
        # forward edge index
        self.adj[u].append([v, cap, None])  # [to, cap, rev_idx placeholder]
        self.adj[v].append([u, 0.0, None])
        self.adj[u][-1][2] = len(self.adj[v]) - 1
        self.adj[v][-1][2] = len(self.adj[u]) - 1
        return (u, len(self.adj[u]) - 1)  # reference to forward edge

    def bfs_level(self, s, t):
        level = [-1] * self.n
        q = deque()
        level[s] = 0
        q.append(s)
        while q:
            u = q.popleft()
            for v, cap, rev in self.adj[u]:
                if cap > EPS and level[v] < 0:
                    level[v] = level[u] + 1
                    q.append(v)
        return level

    def dfs_flow(self, u, t, f, level, it):
        if u == t:
            return f
        for i in range(it[u], len(self.adj[u])):
            it[u] = i
            v, cap, rev = self.adj[u][i]
            if cap > EPS and level[u] + 1 == level[v]:
                pushed = self.dfs_flow(v, t, min(f, cap), level, it)
                if pushed > EPS:
                    # subtract from forward
                    self.adj[u][i][1] -= pushed
                    # add to reverse
                    rev_idx = self.adj[u][i][2]
                    # reverse is at adj[v][rev_idx]
                    self.adj[v][rev_idx][1] += pushed
                    return pushed
        return 0.0

    def max_flow(self, s, t):
        flow = 0.0
        while True:
            level = self.bfs_level(s, t)
            if level[t] < 0:
                break
            it = [0] * self.n
            while True:
                pushed = self.dfs_flow(s, t, INF, level, it)
                if pushed <= EPS:
                    break
                flow += pushed
        return flow

    # helper: get remaining cap of forward edge reference (u, idx)
    def get_edge_cap(self, ref):
        u, idx = ref
        return self.adj[u][idx][1]


def main():
    data = json.load(sys.stdin)

    nodes_list = data.get("nodes", [])
    edges_in = data.get("edges", [])
    sources = data.get("sources", {})  # mapping name->supply
    sink_name = data.get("sink")
    node_caps = data.get("node_caps", {})

    # Total supply
    total_supply = 0.0
    for sname, val in sources.items():
        total_supply += float(val)

    # Map each original node to indices in graph (in_idx, out_idx)
    idx_counter = 0
    in_idx = {}
    out_idx = {}
    for name in nodes_list:
        # do not split source or sink
        if (name in node_caps) and (name != sink_name) and (name not in sources):
            in_idx[name] = idx_counter; idx_counter += 1
            out_idx[name] = idx_counter; idx_counter += 1
        else:
            # single node (no splitting)
            in_idx[name] = idx_counter
            out_idx[name] = idx_counter
            idx_counter += 1

    # We'll build graph with these node-indices, plus s_star and t_star later.
    # For node-splitting, if split, add an edge in->out with capacity=node_caps[name]
    # We'll need adjacency after we create Dinic, so record splitting edges to add.
    splitting_edges = []
    for name in nodes_list:
        if in_idx[name] != out_idx[name]:
            cap = float(node_caps.get(name, 0.0))
            splitting_edges.append((name, in_idx[name], out_idx[name], cap))

    # For each original edge, create transformed edge u_out -> v_in with cap = hi - lo
    # Record lower bounds per edge for reconstruction.
    transformed_edges = []  # each: (u_out_idx, v_in_idx, lo, hi)
    # Also check for invalid hi < lo
    for e in edges_in:
        u = e["from"]; v = e["to"]
        lo = float(e.get("lo", 0.0))
        hi = float(e.get("hi", 0.0))
        if hi + EPS < lo:
            # infeasible bounds
            out = {"status": "infeasible", "reason": "edge hi < lo", "edge": e}
            json.dump(out, sys.stdout)
            return
        u_out = out_idx[u]
        v_in = in_idx[v]
        transformed_edges.append((u_out, v_in, lo, hi))

    # Prepare sums of lower bounds per original node (but mapped to in/out indices)
    sum_in_lo = defaultdict(float)   # keyed by node_in index
    sum_out_lo = defaultdict(float)  # keyed by node_out index
    for (u_out, v_in, lo, hi) in transformed_edges:
        sum_out_lo[u_out] += lo
        sum_in_lo[v_in] += lo

    # Prepare s(v): supply per original node (attached to original node)
    # We'll use the original node mapping: s(v) positive for supply from sources,
    # sink has negative of total supply.
    s_map = {}
    for name in nodes_list:
        s_map[name] = 0.0
    for name, val in sources.items():
        s_map[name] = float(val)
    if sink_name is None:
        # no sink provided -> infeasible
        out = {"status": "infeasible", "reason": "no sink provided"}
        json.dump(out, sys.stdout)
        return
    s_map[sink_name] = s_map.get(sink_name, 0.0) - total_supply  # sink demand

    # Now build full node-level b(v) = s(v) + sum_in_lo - sum_out_lo
    # but we need sums at the transformed indices: use in_idx for sum_in, out_idx for sum_out
    b_pos_sum = 0.0
    b_vals_in_side = {}   # attach positive-side to node_in
    b_vals_out_side = {}  # attach negative-side to node_out
    for name in nodes_list:
        s_val = float(s_map.get(name, 0.0))
        node_in_i = in_idx[name]
        node_out_i = out_idx[name]
        in_lo = sum_in_lo.get(node_in_i, 0.0)
        out_lo = sum_out_lo.get(node_out_i, 0.0)
        b = s_val + in_lo - out_lo
        # If b > 0, we will need s* -> node_in cap b
        # If b < 0, we will need node_out -> t* cap -b
        if b > EPS:
            b_vals_in_side[node_in_i] = b
            b_pos_sum += b
        elif b < -EPS:
            b_vals_out_side[node_out_i] = -b

    # Build Dinic graph
    # Node indices: 0..idx_counter-1 are the transformed node indices
    # Add s_star = idx_counter, t_star = idx_counter+1
    S_star = idx_counter
    T_star = idx_counter + 1
    N = idx_counter + 2
    dinic = Dinic(N)

    # Add splitting edges (node caps) and keep refs for diagnostics
    splitting_refs = []  # (name, in_idx, out_idx, ref, cap)
    for (name, u, v, cap) in splitting_edges:
        ref = dinic.add_edge(u, v, float(cap))
        splitting_refs.append((name, u, v, ref, float(cap)))

    # Add transformed edges with capacity hi-lo and remember references.
    edge_refs = []  # for each original edge in same order, store (u_out, forward_ref, lo, orig_from, orig_to, cap)
    for idx, (u_out, v_in, lo, hi) in enumerate(transformed_edges):
        capp = float(hi - lo)
        # add and store forward edge reference
        ref = dinic.add_edge(u_out, v_in, capp)
        edge_refs.append((u_out, ref, lo, edges_in[idx]["from"], edges_in[idx]["to"], capp))

    # Add super-source and super-sink connections according to b_vals
    for node_in_i, b in b_vals_in_side.items():
        dinic.add_edge(S_star, node_in_i, float(b))
    for node_out_i, b in b_vals_out_side.items():
        dinic.add_edge(node_out_i, T_star, float(b))

    # Run maxflow from S_star to T_star to check lower-bound feasibility
    maxflow_stars = dinic.max_flow(S_star, T_star)

    # Compare to sum of positive b's
    if maxflow_stars + 1e-6 < b_pos_sum:
        # infeasible. compute reachable set from S_star in residual graph for certificate
        visited = [False] * dinic.n
        q = deque([S_star])
        visited[S_star] = True
        while q:
            u = q.popleft()
            for v, cap, rev in dinic.adj[u]:
                if cap > EPS and not visited[v]:
                    visited[v] = True
                    q.append(v)
        # Map visited indices back to original node names
        reachable = set()
        for name in nodes_list:
            if visited[in_idx[name]] or visited[out_idx[name]]:
                reachable.add(name)

        # Identify tight_nodes: split nodes within reachable whose splitting edge is saturated
        tight_nodes = []
        for (name, u, v, ref, cap) in splitting_refs:
            # if node in reachable (in-side reachable) and splitting edge has no remaining capacity
            if visited[u] and dinic.get_edge_cap(ref) <= EPS:
                tight_nodes.append(name)

        # Identify tight_edges: original edges that go from reachable to unreachable and are saturated
        tight_edges = []
        for (u_out, ref, lo, orig_from, orig_to, cap) in edge_refs:
            v_in = in_idx[orig_to]
            if visited[u_out] and not visited[v_in] and dinic.get_edge_cap(ref) <= EPS:
                # flow_needed: the lower bound that must be pushed on this edge (lo)
                # This is a conservative estimate consistent with typical lower-bound certificates
                tight_edges.append({
                    "from": orig_from,
                    "to": orig_to,
                    "flow_needed": lo
                })

        deficit_val = b_pos_sum - maxflow_stars
        # format demand_balance nicely: if nearly integer, show as int
        if abs(round(deficit_val) - deficit_val) < 1e-6:
            demand_balance = int(round(deficit_val))
        else:
            demand_balance = deficit_val

        out = {
            "status": "infeasible",
            "cut_reachable": sorted(list(reachable)),
            "deficit": {
                "demand_balance": demand_balance,
                "tight_nodes": sorted(tight_nodes),
                "tight_edges": tight_edges
            }
        }
        json.dump(out, sys.stdout)
        return

    # If feasible, reconstruct flows: flows on original edges = flow_used_on_ref + lo
    # flow_used_on_ref = orig_cap (cap' = hi-lo) - remaining cap stored at forward edge
    flows = []
    # compute flow into sink to report max_flow_per_min
    flow_into_sink = 0.0
    # For quick lookup: identify which transformed edges target the sink node (original sink in_idx)
    sink_in_idx = in_idx[sink_name]
    sink_out_idx = out_idx[sink_name]

    for (u_out, ref, lo, orig_from, orig_to, orig_cap) in edge_refs:
        u_ref, idx_in_adj = ref
        remaining_cap = dinic.get_edge_cap(ref)
        used = orig_cap - remaining_cap
        if used < 0 and used > -EPS:
            used = 0.0
        final_flow = used + lo
        # clamp tiny negative to 0
        if final_flow < EPS:
            final_flow = 0.0
        flows.append({"from": orig_from, "to": orig_to, "flow": final_flow})
        # if this edge's v_in corresponds to sink's in index, count it as flow into sink
        # Need to find the v_in index: we can recompute v_in from mapping edges_in list
        # But we have orig_to; check if orig_to == sink_name
        if orig_to == sink_name:
            flow_into_sink += final_flow

    # As a sanity: flow_into_sink should equal total_supply within EPS
    # But sometimes routing includes internal cycles; still we report flow_into_sink
    # Build output
    out = {
        "status": "ok",
        "max_flow_per_min": flow_into_sink,
        "flows": flows
    }
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
