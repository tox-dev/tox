from __future__ import absolute_import, unicode_literals

import os
import re
import sys
from collections import OrderedDict

PATTERN = re.compile(r"^(?P<impl>[a-zA-Z]+)(?P<version>[0-9.]+)?(?:-(?P<arch>32|64))?$")
IS_WIN = sys.platform == "win32"


class PythonSpec:
    """Contains specification about a Python Interpreter"""

    def __init__(self, str_spec, implementation, major, minor, patch, architecture, path):
        self.str_spec = str_spec
        self.implementation = implementation
        self.major = major
        self.minor = minor
        self.patch = patch
        self.architecture = architecture
        self.path = path

    @classmethod
    def from_string_spec(cls, string_spec):
        impl, major, minor, patch, arch, path = None, None, None, None, None, None
        if os.path.isabs(string_spec):
            path = string_spec
        else:
            ok = False
            match = re.match(PATTERN, string_spec)
            if match:

                def _int_or_none(val):
                    return None if val is None else int(val)

                try:
                    groups = match.groupdict()
                    version = groups["version"]
                    if version is not None:
                        versions = tuple(int(i) for i in version.split(".") if i)
                        if len(versions) > 3:
                            raise ValueError
                        if len(versions) == 3:
                            major, minor, patch = versions
                        elif len(versions) == 2:
                            major, minor = versions
                        elif len(versions) == 1:
                            version_data = versions[0]
                            major = int(str(version_data)[0])  # first digit major
                            if version_data > 9:
                                minor = int(str(version_data)[1:])
                        ok = True
                except ValueError:
                    pass
                else:
                    impl = groups["impl"]
                    if impl == "py" or impl == "python":
                        impl = "CPython"
                    arch = _int_or_none(groups["arch"])

            if not ok:
                path = string_spec

        return cls(string_spec, impl, major, minor, patch, arch, path)

    def generate_paths(self):
        impls = []
        if self.implementation:
            # first consider implementation  as lower case
            name = self.implementation.lower()
            if name == "cpython":  # convention
                name = "python"
            impls.append(name)
            if not IS_WIN:  # windows is case insensitive, so also consider implementation as it is
                impls.append(self.implementation)
        impls.append("python")  # finally consider python as alias
        impls = list(OrderedDict.fromkeys(impls))
        version = self.major, self.minor, self.patch
        try:
            version = version[: version.index(None)]
        except ValueError:
            pass
        for impl in impls:
            for at in range(len(version)):
                cur_ver = version[: len(version) - at]
                spec = "{}{}".format(impl, ".".join(str(i) for i in cur_ver))
                yield spec

    @property
    def is_abs(self):
        return self.path is not None and os.path.isabs(self.path)

    def satisfies(self, req):
        if req.is_abs and self.is_abs and self.path != req.path:
            return False
        if req.implementation is not None and req.implementation != self.implementation:
            return False
        if req.architecture is not None and req.architecture != self.architecture:
            return False

        ok = True
        for our, _ in zip((self.major, self.minor, self.patch), (req.major, req.minor, req.patch)):
            if req is not None and (our is None or our < req):
                ok = False
                break
        return ok

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join(
                "{}={}".format(k, getattr(self, k))
                for k in (
                    "str_spec",
                    "implementation",
                    "major",
                    "minor",
                    "patch",
                    "architecture",
                    "path",
                )
                if getattr(self, k) is not None
            ),
        )
