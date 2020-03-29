import json
import sys

into = sys.argv[1]
dist_folder = sys.argv[2]
build_type = sys.argv[3]
extra = json.loads(sys.argv[4])
backend_spec = sys.argv[5]
backend_obj = sys.argv[6] if len(sys.argv) >= 7 else None

# noinspection PyTypeChecker
backend = __import__(backend_spec, fromlist=[None])
if backend_obj:
    backend = getattr(backend, backend_obj)

builder = getattr(backend, "build_{}".format(build_type))
basename = builder(dist_folder, **extra)

with open(into, "w") as file_handler:
    json.dump(basename, file_handler)
