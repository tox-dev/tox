from .legacy import make_sdist
from .isolated import build


def build_package(config, report, session):
    if not config.isolated_build:
        return make_sdist(report, config, session)
    else:
        return build(config, report, session)
