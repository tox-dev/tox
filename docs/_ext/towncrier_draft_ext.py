# fmt: off
# Requires Python 3.6+
"""Sphinx extension for making titles with dates from Git tags."""


import subprocess  # noqa: S404
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Union

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nodes

# isort: split

from docutils import statemachine
from setuptools_scm import get_version

PROJECT_ROOT_DIR = Path(__file__).parents[2].resolve()
TOWNCRIER_DRAFT_CMD = (
    sys.executable, '-m',  # invoke via runpy under the same interpreter
    'towncrier',
    '--draft',  # write to stdout, don't change anything on disk
)


@lru_cache(typed=True)
def _get_changelog_draft_entries(
        target_version: str,
        allow_empty: bool = False,
        working_dir: str = None,
        config_path: str = None,
) -> str:
    """Retrieve the unreleased changelog entries from Towncrier."""
    extra_cli_args = (
        '--version',
        rf'\ {target_version}',  # version value to be used in the RST title
        # NOTE: The escaped space sequence (`\ `) is necessary to address
        # NOTE: a corner case when the towncrier config has something like
        # NOTE: `v{version}` in the title format **and** the directive target
        # NOTE: argument starts with a substitution like `|release|`. And so
        # NOTE: when combined, they'd produce `v|release|` causing RST to not
        # NOTE: substitute the `|release|` part. But adding an escaped space
        # NOTE: solves this: that escaped space renders as an empty string and
        # NOTE: the substitution gets processed properly so the result would
        # NOTE: be something like `v1.0` as expected.
    )
    if config_path is not None:
        # This isn't actually supported by a released version of Towncrier yet:
        # https://github.com/twisted/towncrier/pull/157#issuecomment-666549246
        # https://github.com/twisted/towncrier/issues/269
        extra_cli_args += '--config', str(config_path)
    towncrier_output = subprocess.check_output(  # noqa: S603
        TOWNCRIER_DRAFT_CMD + extra_cli_args,
        cwd=str(working_dir) if working_dir else None,
        universal_newlines=True,
    ).strip()

    if not allow_empty and 'No significant changes' in towncrier_output:
        raise LookupError('There are no unreleased changelog entries so far')

    return towncrier_output


@lru_cache(maxsize=1, typed=True)
def _autodetect_scm_version():
    """Retrieve an SCM-based project version."""
    for scm_checkout_path in Path(__file__).parents:  # noqa: WPS500
        is_scm_checkout = (
            (scm_checkout_path / '.git').exists()
            or (scm_checkout_path / '.hg').exists()
        )
        if is_scm_checkout:
            return get_version(root=scm_checkout_path)
    else:
        raise LookupError("Failed to locate the project's SCM repo")


@lru_cache(maxsize=1, typed=True)
def _get_draft_version_fallback(strategy: str, sphinx_config: Dict[str, Any]):
    """Generate a fallback version string for towncrier draft."""
    known_strategies = {'scm-draft', 'scm', 'draft', 'sphinx-version', 'sphinx-release'}
    if strategy not in known_strategies:
        raise ValueError(
            'Expected "stragegy" to be '
            f'one of {known_strategies!r} but got {strategy!r}',
        )

    if 'sphinx' in strategy:
        return (
            sphinx_config.release
            if 'release' in strategy
            else sphinx_config.version
        )

    draft_msg = '[UNRELEASED DRAFT]'
    msg_chunks = ()
    if 'scm' in strategy:
        msg_chunks += (_autodetect_scm_version(),)
    if 'draft' in strategy:
        msg_chunks += (draft_msg,)

    return ' '.join(msg_chunks)


class TowncrierDraftEntriesDirective(SphinxDirective):
    """Definition of the ``towncrier-draft-entries`` directive."""

    has_content = True  # default: False

    def run(self) -> List[nodes.Node]:
        """Generate a node tree in place of the directive."""
        target_version = self.content[:1][0] if self.content[:1] else None
        if self.content[1:]:  # inner content present
            raise self.error(
                f'Error in "{self.name!s}" directive: '
                'only one argument permitted.',
            )

        config = self.state.document.settings.env.config  # noqa: WPS219
        autoversion_mode = config.towncrier_draft_autoversion_mode
        include_empty = config.towncrier_draft_include_empty

        try:
            draft_changes = _get_changelog_draft_entries(
                target_version
                or _get_draft_version_fallback(autoversion_mode, config),
                allow_empty=include_empty,
                working_dir=config.towncrier_draft_working_directory,
                config_path=config.towncrier_draft_config_path,
            )
        except subprocess.CalledProcessError as proc_exc:
            raise self.error(proc_exc)
        except LookupError:
            return []

        self.state_machine.insert_input(
            statemachine.string2lines(draft_changes),
            '[towncrier draft]',
        )
        return []


def setup(app: Sphinx) -> Dict[str, Union[bool, str]]:
    """Initialize the extension."""
    rebuild_trigger = 'html'  # rebuild full html on settings change
    app.add_config_value(
        'towncrier_draft_config_path',
        default=None,
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'towncrier_draft_autoversion_mode',
        default='scm-draft',
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'towncrier_draft_include_empty',
        default=True,
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'towncrier_draft_working_directory',
        default=None,
        rebuild=rebuild_trigger,
    )
    app.add_directive(
        'towncrier-draft-entries',
        TowncrierDraftEntriesDirective,
    )

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        'version': get_version(root=PROJECT_ROOT_DIR),
    }
