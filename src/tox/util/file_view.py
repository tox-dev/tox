from __future__ import annotations

import logging
import shutil
from itertools import chain
from os.path import commonpath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def create_session_view(package: Path, temp_path: Path) -> Path:
    """Allows using the file after you no longer holding a lock to it by moving it into a temp folder."""
    # we'll number the active instances, and use the max value as session folder for a new build
    # note we cannot change package names as PEP-491 (wheel binary format)
    # is strict about file name structure

    temp_path.mkdir(parents=True, exist_ok=True)
    exists = [i.name for i in temp_path.iterdir()]
    file_id = max(chain((0,), (int(i) for i in exists if str(i).isnumeric())))
    session_dir = temp_path / str(file_id + 1)
    session_dir.mkdir()
    session_package = session_dir / package.name

    shutil.copyfile(package, session_package)
    try:
        common = commonpath((session_package, package))
    except ValueError:  # no shared base (e.g. different Windows drives); only the debug log needs it
        logging.debug("package copied from %s to %s", package, session_package)
    else:
        rel_session, rel_package = session_package.relative_to(common), package.relative_to(common)
        logging.debug("package %s copied to %s (%s)", rel_session, rel_package, common)
    return session_package
