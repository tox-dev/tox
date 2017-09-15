#!/usr/bin/env python3.6
import sys
from pathlib import Path

import re


def main():
    make_user_links()


def make_user_links():
    fragmentsPath = Path(__file__).parents[1] / 'tox' / 'changelog'
    for path in fragmentsPath.glob('*.rst'):
        content = path.read_text()
        content = re.sub(r'@([^,\s]+)', r'`@\1 <https://github.com/\1>`_', content)
        path.write_text(content)


if __name__ == '__main__':
    sys.exit(main())
