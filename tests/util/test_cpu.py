from __future__ import annotations

import multiprocessing
from typing import TYPE_CHECKING

from tox.util.cpu import auto_detect_cpus

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_auto_detect_cpus() -> None:
    num_cpus_actual = multiprocessing.cpu_count()
    assert auto_detect_cpus() == num_cpus_actual


def test_auto_detect_cpus_returns_one_when_cpu_count_throws(mocker: MockerFixture) -> None:
    mocker.patch.object(multiprocessing, "cpu_count", side_effect=NotImplementedError)
    assert auto_detect_cpus() == 1
