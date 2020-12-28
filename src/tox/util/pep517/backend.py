"""Handles communication on the backend side between frontend and backend"""
import json
import sys
import traceback


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
        method = getattr(on_object, name, None)
        if method is None:
            return None
        return method(*args, **kwargs)

    def _exit(self):  # noqa
        return 0

    def _commands(self):
        result = ["_commands", "_exit"]
        result.extend(
            k
            for k in {
                "build_sdist",
                "build_wheel",
                "prepare_metadata_for_build_wheel",
                "get_requires_for_build_wheel",
                "get_requires_for_build_sdist",
            }
            if hasattr(self.backend, k)
        )
        return result


def run(argv):
    backend_proxy = BackendProxy(argv[0], None if len(argv) == 1 else argv[1])
    while True:
        try:
            message = input().strip()
        except EOFError:
            break
        if not message:
            continue
        flush()
        try:
            parsed_message = json.loads(message)
            result_file = parsed_message["result"]
        except Exception:  # noqa
            # ignore messages that are not valid JSON and contain a valid result path
            print(f"Backend: incorrect request to backend: {message}", file=sys.stderr)
            traceback.print_exc()
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
            except Exception as exception:
                traceback.print_exc()
                result["code"] = exception.code if isinstance(exception, SystemExit) else 1
                result["exc_type"] = exception.__class__.__name__
                result["exc_msg"] = str(exception)
            finally:
                with open(result_file, "wt") as file_handler:
                    json.dump(result, file_handler)
                print(f"Backend: Write response {result} to {result_file}")
                flush()


def flush():
    sys.stderr.flush()
    sys.stdout.flush()


if __name__ == "__main__":
    run(sys.argv[1:])
