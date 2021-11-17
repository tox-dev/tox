"""
Expand tox factor expressions to tox environment list.
"""
from __future__ import annotations

import re
from itertools import chain, groupby, product
from typing import Iterator


def filter_for_env(value: str, name: str | None) -> str:
    current = (
        set(chain.from_iterable([(i for i, _ in a) for a in find_factor_groups(name)])) if name is not None else set()
    )
    overall = []
    for factors, content in expand_factors(value):
        if factors is None:
            if content:
                overall.append(content)
        else:
            for group in factors:
                if all((a_name in current) ^ negate for a_name, negate in group):
                    overall.append(content)
    result = "\n".join(overall)
    return result


def find_envs(value: str) -> Iterator[str]:
    seen = set()
    for factors, _ in expand_factors(value):
        if factors is not None:
            for group in factors:
                env = explode_factor(group)
                if env not in seen:
                    yield env
                    seen.add(env)


def extend_factors(value: str) -> Iterator[str]:
    for group in find_factor_groups(value):
        yield explode_factor(group)


def explode_factor(group: list[tuple[str, bool]]) -> str:
    return "-".join([name for name, _ in group])


def expand_factors(value: str) -> Iterator[tuple[Iterator[list[tuple[str, bool]]] | None, str]]:
    for line in value.split("\n"):
        match = re.match(r"^((?P<factor_expr>[\w{}.!,-]+):\s+)?(?P<content>.*?)$", line)
        if match is None:  # pragma: no cover
            raise RuntimeError("for a valid factor regex this cannot happen")
        groups = match.groupdict()
        factor_expr, content = groups["factor_expr"], groups["content"]
        if factor_expr is not None:
            factors = find_factor_groups(factor_expr)
            yield factors, content
        else:
            yield None, content


def find_factor_groups(value: str) -> Iterator[list[tuple[str, bool]]]:
    """transform '{py,!pi}-{a,b},c' to [{'py', 'a'}, {'py', 'b'}, {'pi', 'a'}, {'pi', 'b'}, {'c'}]"""
    for env in expand_env_with_negation(value):
        result = [name_with_negate(f) for f in env.split("-")]
        yield result


def expand_env_with_negation(value: str) -> Iterator[str]:
    """transform '{py,!pi}-{a,b},c' to ['py-a', 'py-b', '!pi-a', '!pi-b', 'c']"""
    for key, group in groupby(re.split(r"((?:{[^}]+})+)|,", value), key=bool):
        if key:
            group_str = "".join(group).strip()
            elements = re.split(r"{([^}]+)}", group_str)
            parts = [re.sub(r"\s+", "", elem).split(",") for elem in elements]
            for variant in product(*parts):
                variant_str = "".join(variant)
                yield variant_str


def name_with_negate(factor: str) -> tuple[str, bool]:
    negated = is_negated(factor)
    result = factor[1:] if negated else factor
    return result, negated


def is_negated(factor: str) -> bool:
    return factor.startswith("!")


__all__ = (
    "filter_for_env",
    "find_envs",
    "expand_factors",
    "extend_factors",
)
