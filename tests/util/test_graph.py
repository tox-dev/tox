from collections import OrderedDict
from typing import Dict, Tuple

import pytest

from tox.util.graph import stable_topological_sort


def test_topological_order_empty() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    result = stable_topological_sort(graph)
    assert result == []


def test_topological_order_specified_only() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    graph["A"] = "B", "C"
    result = stable_topological_sort(graph)
    assert result == ["A"]


def test_topological_order() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    graph["A"] = "B", "C"
    graph["B"] = ()
    graph["C"] = ()
    result = stable_topological_sort(graph)
    assert result == ["B", "C", "A"]


def test_topological_order_cycle() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    graph["A"] = "B", "C"
    graph["B"] = ("A",)
    with pytest.raises(ValueError, match="A | B"):
        stable_topological_sort(graph)


def test_topological_complex() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    graph["A"] = "B", "C"
    graph["B"] = "C", "D"
    graph["C"] = ("D",)
    graph["D"] = ()
    result = stable_topological_sort(graph)
    assert result == ["D", "C", "B", "A"]


def test_two_sub_graph() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    graph["F"] = ()
    graph["E"] = ()
    graph["D"] = "E", "F"
    graph["A"] = "B", "C"
    graph["B"] = ()
    graph["C"] = ()

    result = stable_topological_sort(graph)
    assert result == ["F", "E", "D", "B", "C", "A"]


def test_two_sub_graph_circle() -> None:
    graph: Dict[str, Tuple[str, ...]] = OrderedDict()
    graph["F"] = ()
    graph["E"] = ()
    graph["D"] = "E", "F"
    graph["A"] = "B", "C"
    graph["B"] = ("A",)
    graph["C"] = ()
    with pytest.raises(ValueError, match="A | B"):
        stable_topological_sort(graph)
