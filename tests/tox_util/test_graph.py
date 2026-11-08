from __future__ import annotations

from collections import OrderedDict

import pytest

from tox.util.graph import stable_topological_sort


def test_topological_order_empty() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    result = stable_topological_sort(graph)
    assert result == []


def test_topological_order_specified_only() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    graph["A"] = {"B", "C"}
    result = stable_topological_sort(graph)
    assert result == ["A"]


def test_topological_order() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    graph["A"] = {"B", "C"}
    graph["B"] = set()
    graph["C"] = set()
    result = stable_topological_sort(graph)
    assert result == ["B", "C", "A"]


def test_topological_order_cycle() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    graph["A"] = {"B", "C"}
    graph["B"] = {"A"}
    with pytest.raises(ValueError, match=r"^A \| B$"):
        stable_topological_sort(graph)


def test_topological_complex() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    graph["A"] = {"B", "C"}
    graph["B"] = {"C", "D"}
    graph["C"] = {"D"}
    graph["D"] = set()
    result = stable_topological_sort(graph)
    assert result == ["D", "C", "B", "A"]


def test_two_sub_graph() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    graph["F"] = set()
    graph["E"] = set()
    graph["D"] = {"E", "F"}
    graph["A"] = {"B", "C"}
    graph["B"] = set()
    graph["C"] = set()

    result = stable_topological_sort(graph)
    assert result == ["F", "E", "D", "B", "C", "A"]


def test_two_sub_graph_circle() -> None:
    graph: dict[str, set[str]] = OrderedDict()
    graph["F"] = set()
    graph["E"] = set()
    graph["D"] = {"E", "F"}
    graph["A"] = {"B", "C"}
    graph["B"] = {"A"}
    graph["C"] = set()
    with pytest.raises(ValueError, match=r"^A \| B$"):
        stable_topological_sort(graph)
