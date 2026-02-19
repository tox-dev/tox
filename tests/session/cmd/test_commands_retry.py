from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_retry_succeeds_after_failure(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
commands_retry = 3
commands = [["python", "-c", \
"from pathlib import Path; p = Path('counter.txt'); \
c = int(p.read_text()) + 1 if p.exists() else 1; \
p.write_text(str(c)); raise SystemExit(0 if c >= 3 else 1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "command failed (attempt 1 of 4), retrying" in result.out
    assert "command failed (attempt 2 of 4), retrying" in result.out


def test_retry_all_exhausted(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
commands_retry = 2
commands = [["python", "-c", "raise SystemExit(1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_failed(code=1)
    assert "command failed (attempt 1 of 3), retrying" in result.out
    assert "command failed (attempt 2 of 3), retrying" in result.out


def test_retry_default_no_retry(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
commands = [["python", "-c", "raise SystemExit(1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_failed(code=1)
    assert "retrying" not in result.out


def test_retry_dash_prefix_no_retry(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
commands_retry = 3
commands = [["-", "python", "-c", "raise SystemExit(1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "retrying" not in result.out


def test_retry_with_ignore_errors(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
ignore_errors = true
commands_retry = 1
commands = [["python", "-c", "raise SystemExit(1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_failed(code=1)
    assert "command failed (attempt 1 of 2), retrying" in result.out


def test_retry_bang_prefix_succeeds_on_nonzero(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
commands_retry = 2
commands = [["!", "python", "-c", "raise SystemExit(1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "retrying" not in result.out


def test_retry_bang_prefix_retries_on_zero(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": """\
[env_run_base]
package = "skip"
commands_retry = 2
commands = [["!", "python", "-c", \
"from pathlib import Path; p = Path('counter_bang.txt'); \
c = int(p.read_text()) + 1 if p.exists() else 1; \
p.write_text(str(c)); raise SystemExit(0 if c < 3 else 1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "command failed (attempt 1 of 3), retrying" in result.out
    assert "command failed (attempt 2 of 3), retrying" in result.out


@pytest.mark.parametrize("command_key", ["commands_pre", "commands_post"])
def test_retry_applies_to_pre_and_post(tox_project: ToxProjectCreator, command_key: str) -> None:
    proj = tox_project({
        "tox.toml": f"""\
[env_run_base]
package = "skip"
commands_retry = 3
{command_key} = [["python", "-c", \
"from pathlib import Path; p = Path('counter_{command_key}.txt'); \
c = int(p.read_text()) + 1 if p.exists() else 1; \
p.write_text(str(c)); raise SystemExit(0 if c >= 2 else 1)"]]
"""
    })
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "command failed (attempt 1 of 4), retrying" in result.out
