import pytest


@pytest.fixture
def get_option(newconfig):
    def do(tox_ini, option_name, pos_args=()):
        config = newconfig(list(pos_args), tox_ini)
        print(type(config.envconfigs), config.envconfigs.keys())
        return getattr(config.envconfigs["python"], option_name)

    return do
