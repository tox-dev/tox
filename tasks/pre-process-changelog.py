#!/usr/bin/env python3.6
import os
import re
import subprocess
import sys
from pathlib import Path


def main():
    manipulate_the_news()


# todo integrate that into the test/build process somehow
def include_draft_newsfragments():
    """
    generate and include into the changelog news fragments so they are also subject to the CI,
    whenever a new release is done there should be no news fragment and as such this will have
    no effect
    """
    project_root = Path(__file__).parents[1]
    current_path = os.getcwd()
    try:
        os.chdir(project_root)
        cmd = ['towncrier', '--draft', '--dir', project_root]
        out = subprocess.check_output(cmd).decode('utf-8').strip()
        docs_build_dir = project_root / '.tox' / 'docs' / 'fragments.rst'
        docs_build_dir.write(out)
    finally:
        os.chdir(current_path)


def manipulate_the_news():
    home = 'https://github.com'
    issue = '%s/issue' % home
    pull = '%s/pull' % home
    towncrierPath = Path(__file__).parents[1] / 'tox' / 'changelog'
    for pattern, replacement in (
        (r'[^`]@([^,\s]+)', r'`@\1 <%s/\1>`_' % home),
        (r'[^`]#pr([\d]+)', r'`#\1 <%s/\1>`_' % issue),
        (r'[^`]#([\d]+)', r'`#pr\1 <%s/\1>`_' % pull),
    ):
        for path in towncrierPath.glob('*.rst'):
            path.write_text(re.sub(pattern, replacement, path.read_text()))


if __name__ == '__main__':
    sys.exit(main())
