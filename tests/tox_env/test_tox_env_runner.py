from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


def test_package_only(
    tox_project: ToxProjectCreator,
    demo_pkg_inline: Path,
) -> None:
    ini = "[testenv]\ncommands = python -c 'print('foo')'"
    proj = tox_project(
        {"tox.ini": ini, "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text()},
        base=demo_pkg_inline,
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r", "--sdistonly")
    result.assert_success()

    expected_calls = [
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_sdist"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "build_wheel"),
        (".pkg", "build_sdist"),
        (".pkg", "_exit"),
    ]
    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert found_calls == expected_calls
