An environment name that combines an interpreter prefix with an explicit version, such as ``pypy-3.10``, now works
together with other factors. ``pypy-3.10-lint`` or ``tests-cpython-3.13`` used to fail with ``conflicting factors``,
because the prefix and the version were read as two separate Python factors.
