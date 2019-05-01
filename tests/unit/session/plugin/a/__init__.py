import pluggy

hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_addoption(parser):
    parser.add_argument("--option", choices=["a", "b"], default="a", required=False)
