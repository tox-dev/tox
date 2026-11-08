"""Helper methods related to graph theory."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def stable_topological_sort(graph: dict[str, set[str]]) -> list[str]:
    """Sort the nodes of a graph, so that each node comes after the nodes it depends on.

    :param graph: the nodes, each mapped to the nodes it depends on

    :returns: the nodes in order

    :raises ValueError: when the graph has a cycle, with the cycle in the message

    """
    to_order = set(graph.keys())  # keep a log of what  we need to order

    _fill_missing_nodes(graph)

    inverse_graph = defaultdict(set)
    for key, depends in graph.items():
        for depend in depends:
            inverse_graph[depend].add(key)

    degree = {k: len(v) for k, v in graph.items()}
    ready_to_visit = {n for n, d in degree.items() if not d}
    need_to_visit = OrderedDict((i, None) for i in graph)
    topology = []
    while need_to_visit:
        if (node := _next_ready(need_to_visit, ready_to_visit)) is None:
            break
        del need_to_visit[node]

        topology.append(node)

        # decrease degree for nodes we're going too
        for to_node in inverse_graph[node]:
            degree[to_node] -= 1
            if not degree[to_node]:  # if a node has no more incoming node it's ready to visit
                ready_to_visit.add(to_node)

    result = [n for n in topology if n in to_order]  # filter out missing nodes we extended

    if len(result) < len(to_order):
        _identify_cycle(graph)
        msg = "could not order tox environments and failed to detect circle"  # pragma: no cover  # untested error path
        raise ValueError(msg)  # pragma: no cover  # untested error path
    return result


def _fill_missing_nodes(graph: dict[str, set[str]]) -> None:
    for values in list(graph.values()):
        for value in values:
            if value not in graph:
                graph[value] = set()


def _next_ready(need_to_visit: Iterable[str], ready_to_visit: set[str]) -> str | None:
    # to keep stable, pick the first node ready to visit in the original order
    return next((node for node in need_to_visit if node in ready_to_visit), None)


def _identify_cycle(graph: dict[str, set[str]]) -> None:
    """Find a cycle in a graph, to report it when sorting fails.

    :param graph: the nodes, each mapped to the nodes it depends on

    :raises ValueError: with the nodes of the cycle

    """
    path: dict[str, None] = OrderedDict()
    visited = set()

    def visit(vertex: str) -> dict[str, None] | None:
        if vertex in visited:
            return None
        visited.add(vertex)
        path[vertex] = None
        for neighbor in graph.get(vertex, ()):
            if neighbor in path or visit(neighbor):
                return path
        del path[vertex]
        return None

    for node in graph:  # pragma: no branch # we never get here if the graph is empty
        if (result := visit(node)) is not None:
            msg = f"{' | '.join(result.keys())}"
            raise ValueError(msg)


__all__ = [
    "stable_topological_sort",
]
