import sys

backend_spec = sys.argv[1]
backend_obj = sys.argv[2]


backend = __import__(backend_spec, fromlist=[None])
if backend_obj:
    backend = getattr(backend, backend_obj)

dist_folder = sys.argv[3]

basename = backend.build_sdist(dist_folder, {"--global-option": ["--formats=gztar"]})
print(basename)
