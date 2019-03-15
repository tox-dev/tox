import sys

if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:
    import contextlib


    @contextlib.contextmanager
    def nullcontext(enter_result=None):
        yield enter_result
