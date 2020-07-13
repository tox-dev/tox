"""PEP 517 build backend invocation script.

It accepts externally parsed build configuration from `[build-system]`
in `pyproject.toml` and invokes an API endpoint for building an sdist
tarball.
"""

import os
import sys

dist_folder = sys.argv[1]
backend_spec = sys.argv[2]
backend_obj = sys.argv[3] if len(sys.argv) >= 4 else None
backend_paths = sys.argv[4].split(os.path.pathsep) if sys.argv[4] else []

sys.path[:0] = backend_paths

backend = __import__(backend_spec, fromlist=["_trash"])
if backend_obj:
    backend = getattr(backend, backend_obj)

basename = backend.build_sdist(dist_folder, {"--global-option": ["--formats=gztar"]})
print(basename)
