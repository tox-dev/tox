import json
from pathlib import Path
from pprint import pprint
from typing import Any, List

import pytest

from tox.pytest import ToxProjectCreator


@pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
@pytest.mark.parametrize(("posargs", "expected"), [([], ["probe.py"]), (["foo"], ["probe.py", "foo"])])
def test_gh1928(  # noqa: SC200
    tox_project: ToxProjectCreator,
    tmp_path: Path,
    enable_pip_pypi_access: Any,  # noqa: U100
    posargs: List[str],  # noqa: SC200
    expected: List[str],
) -> None:
    out_path = tmp_path / "out.json"
    project = tox_project(
        {
            "tox.ini": """
                [testenv]
                commands=python probe.py []
            """,
            "pyproject.toml": """
                [build-system]
                requires = ["setuptools"]
                build-backend = 'setuptools.build_meta'
            """,
            "probe.py": f"""
                import json
                import sys

                with open({str(out_path)!r}, 'w') as out:
                    json.dump(sys.argv, out)
            """,
        }
    )

    outcome = project.run("--", *posargs)  # noqa: SC200
    pprint(outcome)

    with out_path.open() as result:
        assert json.load(result) == expected
