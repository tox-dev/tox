from tox.util.graph import stable_topological_sort


def test_topological_order():
    stable_topological_sort({"A": ("B", "C")})
