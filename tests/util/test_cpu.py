from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest

from tox.util.cpu import auto_detect_cpus

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture


@pytest.fixture
def two_cpu_affinity() -> Iterator[None]:
    original = os.sched_getaffinity(0)
    os.sched_setaffinity(0, sorted(original)[:2])
    yield
    os.sched_setaffinity(0, original)


@pytest.mark.skipif(
    not hasattr(os, "sched_setaffinity") or len(os.sched_getaffinity(0)) < 3,
    reason="needs a CPU affinity API and at least three usable CPUs",
)
@pytest.mark.usefixtures("two_cpu_affinity")
def test_auto_detect_cpus_honours_affinity() -> None:
    assert auto_detect_cpus() == 2


@pytest.mark.skipif(sys.version_info >= (3, 13), reason="3.13+ asks os.process_cpu_count")
def test_auto_detect_cpus_without_affinity(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    mocker.patch.object(os, "cpu_count", return_value=5)
    assert auto_detect_cpus() == 5


def test_auto_detect_cpus_returns_one_when_count_is_unknown(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    mocker.patch.object(os, "process_cpu_count", create=True, return_value=None)
    mocker.patch.object(os, "cpu_count", return_value=None)
    assert auto_detect_cpus() == 1
