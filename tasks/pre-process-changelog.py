#!/usr/bin/env python3.6
import re
import sys
from pathlib import Path


def main():
    manipulate_the_news()


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
