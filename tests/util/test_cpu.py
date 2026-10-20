from __future__ import annotations

import os
import sys

import pytest

from tox.util.cpu import auto_detect_cpus


@pytest.mark.skipif(sys.version_info < (3, 13), reason="os.process_cpu_count is new in 3.13")
def test_auto_detect_cpus_uses_process_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "process_cpu_count", lambda: 3)
    monkeypatch.setattr(os, "cpu_count", lambda: 64)
    assert auto_detect_cpus() == 3


@pytest.mark.skipif(sys.version_info >= (3, 13), reason="3.13+ asks os.process_cpu_count")
def test_auto_detect_cpus_honours_affinity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "sched_getaffinity", lambda _pid: {0, 2, 5}, raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 64)
    assert auto_detect_cpus() == 3


@pytest.mark.skipif(sys.version_info >= (3, 13), reason="3.13+ asks os.process_cpu_count")
def test_auto_detect_cpus_without_affinity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: 5)
    assert auto_detect_cpus() == 5


def test_auto_detect_cpus_returns_one_when_count_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(os, "sched_getaffinity", raising=False)
    monkeypatch.setattr(os, "process_cpu_count", lambda: None, raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert auto_detect_cpus() == 1
