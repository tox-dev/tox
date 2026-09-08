import sys

from typing_extensions import deprecated

# urllib.request re-exports these on Windows before 3.14; typeshed deprecates those aliases too.
if sys.version_info >= (3, 14):
    @deprecated("Use urllib.request.url2pathname")
    def url2pathname(url: str) -> str: ...
    @deprecated("Use urllib.request.pathname2url")
    def pathname2url(p: str) -> str: ...

else:
    def url2pathname(url: str) -> str: ...
    def pathname2url(p: str) -> str: ...
