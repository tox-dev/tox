from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.pytest import ToxProjectCreator


def test_inline_tox_py(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover # the code is copied to a python file
        import logging  # noqa: PLC0415

        from tox.plugin import impl  # noqa: PLC0415

        @impl
        def tox_add_option(parser: ToxParser) -> None:
            logging.warning("Add magic")
            parser.add_argument("--magic", action="store_true")

    project = tox_project({"toxfile.py": plugin})
    result = project.run("-h")
    result.assert_success()
    assert "--magic" in result.out
