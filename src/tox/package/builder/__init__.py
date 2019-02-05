from .legacy import make_sdist
from .isolated import build


def build_package(config, session):
    if not config.isolated_build:
        return make_sdist(config, session)
    else:
        return build(config, session)
