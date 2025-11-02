#!/usr/bin/env python3
"""
Belts: Max flow with lower bounds and node capacities.
Reads JSON from stdin, writes JSON to stdout.
"""

import json
import sys
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional

TOL = 1e-9


class MaxFlowSolver:
    """Max flow solver using Dinic's algorithm with lower bounds and node caps."""
    
    def __init__(self):
        self.graph = defaultdict(lambda: defaultdict(float))
        self.nodes = set()
        
    def add_edge(self, u: str, v: str, capacity: float):
        """Add edge with capacity."""
        self.nodes.add(u)
        self.nodes.add(v)
        
        if capacity > TOL:
            self.graph[u][v] += capacity
            
    def bfs(self, source: str, sink: str) -> Dict[str, int]:
        """BFS to compute level graph."""
        level = {source: 0}
        queue = deque([source])
        
        while queue:
            u = queue.popleft()
            for v in self.graph[u]:
                if v not in level and self.graph[u][v] > TOL:
                    level[v] = level[u] + 1
                    queue.append(v)
                    
        return level
    
    def dfs(self, u: str, sink: str, flow: float, level: Dict[str, int], 
            iter_pos: Dict[str, int]) -> float:
        """DFS to find blocking flow."""
        if u == sink:
            return flow
            
        neighbors = list(self.graph[u].keys())
        
        # Continue from last position to avoid revisiting
        if u not in iter_pos:
            iter_pos[u] = 0
            
        while iter_pos[u] < len(neighbors):
            v = neighbors[iter_pos[u]]
            
            if level.get(v, -1) == level[u] + 1 and self.graph[u][v] > TOL:
                pushed = self.dfs(v, sink, min(flow, self.graph[u][v]), 
                                level, iter_pos)
                
                if pushed > TOL:
                    self.graph[u][v] -= pushed
                    self.graph[v][u] += pushed
                    return pushed
                    
            iter_pos[u] += 1
            
        return 0
    
    def max_flow(self, source: str, sink: str) -> float:
        """Compute max flow using Dinic's algorithm."""
        total_flow = 0
        
        while True:
            level = self.bfs(source, sink)
            
            if sink not in level:
                break
                
            iter_pos = {}
            
            while True:
                pushed = self.dfs(source, sink, float('inf'), level, iter_pos)
                if pushed < TOL:
                    break
                total_flow += pushed
                
        return total_flow
    
    def get_reachable(self, source: str) -> Set[str]:
        """Get nodes reachable from source in residual graph."""
        reachable = {source}
        queue = deque([source])
        
        while queue:
            u = queue.popleft()
            for v in self.graph[u]:
                if v not in reachable and self.graph[u][v] > TOL:
                    reachable.add(v)
                    queue.append(v)
                    
        return reachable


def solve_belts(data: Dict) -> Dict:
    """
    Solve max flow with lower bounds and node capacities.
    
    Strategy:
    1. Split nodes with capacities first
    2. Transform lower bounds to imbalances on the split graph
    3. Check lower bound feasibility
    4. Compute main flow from sources to sink
    5. Reconstruct original flows
    """
    
    nodes = data["nodes"]
    edges = data["edges"]
    sources = data["sources"]
    sink = data["sink"]
    node_caps = data.get("node_caps", {})
    
    # Step 1: Build transformed graph with node splitting
    node_split_map = {}
    all_nodes = set(nodes)
    
    # Split nodes with capacities
    for node in nodes:
        if node in node_caps and node != sink and node not in sources:
            node_in = f"{node}_in"
            node_out = f"{node}_out"
            node_split_map[node] = (node_in, node_out)
            all_nodes.add(node_in)
            all_nodes.add(node_out)
            all_nodes.discard(node)
    
    # Helper to map node names
    def map_node(node: str, is_source: bool) -> str:
        """Map node to split version. is_source=True means we're coming FROM this node."""
        if node in node_split_map:
            return node_split_map[node][1] if is_source else node_split_map[node][0]
        return node
    
    # Build transformed edges
    transformed_edges = []
    
    # Add split edges for node capacities
    for node in nodes:
        if node in node_caps and node != sink and node not in sources:
            node_in, node_out = node_split_map[node]
            transformed_edges.append({
                "from": node_in,
                "to": node_out,
                "lo": 0,
                "hi": node_caps[node],
                "is_split_edge": True,
                "original_node": node
            })
    
    # Add original edges (mapped to split nodes)
    for edge in edges:
        u = map_node(edge["from"], is_source=True)
        v = map_node(edge["to"], is_source=False)
        
        transformed_edges.append({
            "from": u,
            "to": v,
            "lo": edge.get("lo", 0),
            "hi": edge.get("hi", float('inf')),
            "is_split_edge": False,
            "original_from": edge["from"],
            "original_to": edge["to"]
        })
    
    # Step 2: Transform lower bounds - compute imbalances
    imbalance = defaultdict(float)
    reduced_edges = []
    edge_lower_bounds = {}
    
    for edge in transformed_edges:
        u = edge["from"]
        v = edge["to"]
        lo = edge["lo"]
        hi = edge["hi"]
        
        # Store original lower bound
        edge_lower_bounds[(u, v)] = lo
        
        # Reduce capacity
        reduced_cap = hi - lo
        reduced_edges.append((u, v, reduced_cap))
        
        # Track imbalance from lower bounds
        if lo > TOL:
            imbalance[u] -= lo  # u must send at least lo
            imbalance[v] += lo  # v receives at least lo
    
    # Step 3: Check lower bound feasibility with super source/sink
    super_source = "__super_source__"
    super_sink = "__super_sink__"
    
    lb_solver = MaxFlowSolver()
    
    total_demand = 0
    total_supply = 0
    
    for node in all_nodes:
        imb = imbalance[node]
        if imb > TOL:  # Positive imbalance = needs incoming flow
            lb_solver.add_edge(super_source, node, imb)
            total_demand += imb
        elif imb < -TOL:  # Negative imbalance = has outgoing flow
            lb_solver.add_edge(node, super_sink, -imb)
            total_supply += -imb
    
    # Add all reduced capacity edges to feasibility graph
    for u, v, cap in reduced_edges:
        if cap > TOL:
            lb_solver.add_edge(u, v, cap)
    
    # Check if lower bounds are satisfiable
    if total_demand > TOL:
        lb_flow = lb_solver.max_flow(super_source, super_sink)
        
        if abs(lb_flow - total_demand) > TOL:
            # Lower bounds infeasible
            reachable = lb_solver.get_reachable(super_source)
            reachable.discard(super_source)
            
            # Map back to original node names
            original_reachable = []
            for node in reachable:
                found = False
                for orig, (nin, nout) in node_split_map.items():
                    if node == nin or node == nout:
                        if orig not in original_reachable:
                            original_reachable.append(orig)
                        found = True
                        break
                if not found:
                    original_reachable.append(node)
            
            tight_edges = []
            for u, v, cap in reduced_edges:
                if u in reachable and v not in reachable:
                    flow_used = cap - lb_solver.graph[u].get(v, 0)
                    if flow_used >= cap - TOL:
                        tight_edges.append({
                            "from": u,
                            "to": v,
                            "flow_needed": round(cap, 2)
                        })
            
            return {
                "status": "infeasible",
                "cut_reachable": sorted(original_reachable),
                "deficit": {
                    "demand_balance": round(total_demand - lb_flow, 2),
                    "tight_nodes": [],
                    "tight_edges": tight_edges[:3]
                }
            }
    
    # Step 4: Compute main flow from sources to sink
    main_solver = MaxFlowSolver()
    
    # Add all reduced capacity edges
    for u, v, cap in reduced_edges:
        if cap > TOL:
            main_solver.add_edge(u, v, cap)
    
    # Add edges from virtual source to actual sources
    virtual_source = "__virtual_source__"
    total_supply_amount = 0
    
    for src, supply in sources.items():
        src_node = map_node(src, is_source=True)
        main_solver.add_edge(virtual_source, src_node, supply)
        total_supply_amount += supply
    
    # Find sink node (might be mapped)
    sink_node = map_node(sink, is_source=False)
    
    max_flow_value = main_solver.max_flow(virtual_source, sink_node)
    
    # Check if we can push all supply to sink
    if abs(max_flow_value - total_supply_amount) > TOL:
        # Main flow infeasible
        reachable = main_solver.get_reachable(virtual_source)
        reachable.discard(virtual_source)
        
        # Map back to original nodes
        original_reachable = []
        for node in reachable:
            found = False
            for orig, (nin, nout) in node_split_map.items():
                if node == nin or node == nout:
                    if orig not in original_reachable:
                        original_reachable.append(orig)
                    found = True
                    break
            if not found:
                original_reachable.append(node)
        
        tight_edges = []
        for u, v, cap in reduced_edges:
            if u in reachable and v not in reachable:
                flow_used = cap - main_solver.graph[u].get(v, 0)
                if flow_used >= cap - TOL:
                    # Map back to original edge
                    orig_u = u
                    orig_v = v
                    for orig, (nin, nout) in node_split_map.items():
                        if u == nout:
                            orig_u = orig
                        if v == nin:
                            orig_v = orig
                    
                    tight_edges.append({
                        "from": orig_u,
                        "to": orig_v,
                        "flow_needed": round(cap, 2)
                    })
        
        return {
            "status": "infeasible",
            "cut_reachable": sorted(original_reachable),
            "deficit": {
                "demand_balance": round(total_supply_amount - max_flow_value, 2),
                "tight_nodes": [],
                "tight_edges": tight_edges[:3]
            }
        }
    
    # Step 5: Reconstruct original flows by adding back lower bounds
    flows = []
    
    for edge in transformed_edges:
        # Skip split edges in output
        if edge.get("is_split_edge", False):
            continue
        
        u = edge["from"]
        v = edge["to"]
        lo = edge["lo"]
        
        # Get flow on reduced edge from main solver
        reduced_cap = edge["hi"] - lo
        residual = main_solver.graph[u].get(v, 0)
        reduced_flow = max(0, reduced_cap - residual)
        
        # Original flow = reduced flow + lower bound
        original_flow = reduced_flow + lo
        
        if original_flow > TOL:
            flows.append({
                "from": edge["original_from"],
                "to": edge["original_to"],
                "flow": round(original_flow, 2)
            })
    
    # Sort flows for determinism
    flows.sort(key=lambda x: (x["from"], x["to"]))
    
    return {
        "status": "ok",
        "max_flow_per_min": round(max_flow_value, 2),
        "flows": flows
    }


def main():
    """Read JSON from stdin, solve, write JSON to stdout."""
    data = json.load(sys.stdin)
    result = solve_belts(data)
    print(json.dumps(result, separators=(',', ':')))


if __name__ == "__main__":
    main()