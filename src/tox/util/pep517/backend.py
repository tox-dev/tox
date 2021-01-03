"""Handles communication on the backend side between frontend and backend"""
import json
import sys
import traceback


class MissingCommand(TypeError):
    """Missing command"""


class BackendProxy:
    def __init__(self, backend_module, backend_obj):
        self.backend_module = backend_module
        self.backend_object = backend_obj
        backend = __import__(self.backend_module, fromlist=[None])  # type: ignore[list-item]
        if self.backend_object:
            backend = getattr(backend, self.backend_object)
        self.backend = backend

    def __call__(self, name, *args, **kwargs):
        on_object = self if name.startswith("_") else self.backend
        if not hasattr(on_object, name):
            raise MissingCommand(f"{on_object!r} has no attribute {name!r}")
        return getattr(on_object, name)(*args, **kwargs)

    def __str__(self):
        return f"{self.__class__.__name__}(backend={self.backend})"

    def _exit(self):  # noqa
        return 0


def flush():
    sys.stderr.flush()
    sys.stdout.flush()


def run(argv):
    reuse_process = argv[0].lower() == "true"
    try:
        backend_proxy = BackendProxy(argv[1], None if len(argv) == 2 else argv[2])
    except BaseException:
        print("failed to start backend", file=sys.stderr)
        flush()
        raise
    print(f"started backend {backend_proxy}", file=sys.stdout)
    while True:
        try:
            message = input().strip()
        except EOFError:  # pragma: no cover # when the stdout is closed without exit
            break  # pragma: no cover
        if not message:
            continue
        flush()  # flush any output generated before
        try:
            parsed_message = json.loads(message)
            result_file = parsed_message["result"]
        except Exception:  # noqa
            # ignore messages that are not valid JSON and contain a valid result path
            print(f"Backend: incorrect request to backend: {message}", file=sys.stderr)
            flush()
        else:
            result = {}
            try:
                cmd = parsed_message["cmd"]
                print("Backend: run command {} with args {}".format(cmd, parsed_message["kwargs"]))
                outcome = backend_proxy(parsed_message["cmd"], **parsed_message["kwargs"])
                result["return"] = outcome
                if cmd == "_exit":
                    break
            except BaseException as exception:
                result["code"] = exception.code if isinstance(exception, SystemExit) else 1
                result["exc_type"] = exception.__class__.__name__
                result["exc_msg"] = str(exception)
                if not isinstance(exception, MissingCommand):  # for missing command do not print stack
                    traceback.print_exc()
                if not isinstance(exception, Exception):  # allow SystemExit/KeyboardInterrupt to go through
                    raise
            finally:
                try:
                    with open(result_file, "wt") as file_handler:
                        json.dump(result, file_handler)
                except Exception:  # noqa
                    traceback.print_exc()
                finally:
                    print(f"Backend: Wrote response {result} to {result_file}")  # used as done marker by frontend
                    flush()  # pragma: no branch
        if reuse_process is False:  # pragma: no branch # no test for reuse process in root test env
            break
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
