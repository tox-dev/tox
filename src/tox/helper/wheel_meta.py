"""
Get projects metadata per PEP-517.
"""
import json
import sys

into = sys.argv[1]
extra = json.loads(sys.argv[2])
backend_spec = sys.argv[3]
backend_obj = sys.argv[4] if len(sys.argv) >= 5 else None


backend = __import__(backend_spec, fromlist=[None])  # type: ignore # noqa
if backend_obj:
    backend = getattr(backend, backend_obj)

for_build_requires = backend.prepare_metadata_for_build_wheel(into, **extra)
