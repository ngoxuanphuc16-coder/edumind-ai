"""Xây dựng DAG từ KG triplet (implementation_plan.md mục 4).

KG trích xuất tự động không đảm bảo phi chu trình -- phát hiện & phá chu trình
(loại cạnh có confidence thấp nhất trong chu trình) TRƯỚC KHI chạy topological sort.
"""

from typing import List, Tuple

import networkx as nx

from app.graph.state import KGTriplet


def detect_and_break_cycles(triplets: List[KGTriplet]) -> Tuple[List[KGTriplet], List[tuple]]:
    g = nx.DiGraph()
    for t in triplets:
        g.add_edge(t["subject"], t["object"], confidence=t.get("confidence", 0.5))

    broken = []
    while True:
        try:
            cycle = nx.find_cycle(g)
        except nx.NetworkXNoCycle:
            break
        weakest = min(cycle, key=lambda e: g[e[0]][e[1]]["confidence"])
        g.remove_edge(weakest[0], weakest[1])
        broken.append(weakest)

    remaining = [t for t in triplets if g.has_edge(t["subject"], t["object"])]
    return remaining, broken


def topological_sort(triplets: List[KGTriplet]) -> List[str]:
    g = nx.DiGraph()
    for t in triplets:
        g.add_edge(t["subject"], t["object"])
    if g.number_of_nodes() == 0:
        return []
    return list(nx.topological_sort(g))
